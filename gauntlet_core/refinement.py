from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Protocol

from .analysis import analyze_paper_text, trim_sentence
from .models import AnalysisReport, AuditEvent, utc_now_iso


DEFAULT_OPENAI_MODEL = "gpt-4.1"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
PROVIDER_ORDER = ("Gemini", "OpenAI", "Anthropic")
DEFAULT_PROVIDER_MODELS = {
    "Gemini": DEFAULT_GEMINI_MODEL,
    "OpenAI": DEFAULT_OPENAI_MODEL,
    "Anthropic": DEFAULT_ANTHROPIC_MODEL,
}
DEFAULT_CRITIC_PROVIDER = "Gemini"
DEFAULT_CHALLENGER_PROVIDER = "Anthropic"

SYSTEM_PROMPT = """You are working inside The Gauntlet's optional refinement chamber.
Do not rewrite the paper. Produce visible critique and repair planning only.
Use evidence-first language, avoid treating any theory as final authority, and do not reveal hidden reasoning.
Every suggestion must point back to a specific claim, gap, contradiction, or evidence requirement."""


class RefinementError(RuntimeError):
    pass


class RefinementClient(Protocol):
    provider: str

    def complete(self, prompt: str, model: str) -> str:
        ...


@dataclass(frozen=True)
class ProviderSelection:
    role: str
    provider: str
    model: str
    api_key: str = ""


@dataclass(frozen=True)
class ModelTurn:
    provider: str
    model: str
    prompt: str
    response: str
    status: str
    role: str = "model"


@dataclass(frozen=True)
class RefinementReport:
    source_name: str
    created_at: str
    deterministic_verdict: str
    issue_brief: str
    critic_turn: ModelTurn
    challenger_turn: ModelTurn
    disagreements: list[str]
    repair_plan: str
    recheck_report: AnalysisReport
    audit_events: list[AuditEvent]

    @property
    def turns(self) -> list[ModelTurn]:
        return [self.critic_turn, self.challenger_turn]

    @property
    def openai_turn(self) -> ModelTurn:
        return self.critic_turn

    @property
    def anthropic_turn(self) -> ModelTurn:
        return self.challenger_turn

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_markdown(self) -> str:
        disagreements = "\n".join(f"- {item}" for item in self.disagreements) or "- No explicit disagreements detected."
        return "\n".join(
            [
                f"# The Gauntlet Refinement Report: {self.source_name}",
                "",
                f"- Deterministic verdict: **{self.deterministic_verdict}**",
                f"- Repair-plan re-check verdict: **{self.recheck_report.verdict}**",
                f"- Generated: {self.created_at}",
                "",
                "## Issue Brief",
                "",
                self.issue_brief,
                "",
                f"## {self.critic_turn.provider} Critique",
                "",
                self.critic_turn.response,
                "",
                f"## {self.challenger_turn.provider} Challenge",
                "",
                self.challenger_turn.response,
                "",
                "## Disagreements And Remaining Tension",
                "",
                disagreements,
                "",
                "## Repair Plan",
                "",
                self.repair_plan,
                "",
                "## Re-Check Summary",
                "",
                self.recheck_report.summary,
                "",
                "_API keys are supplied by the user for the session and are not saved by The Gauntlet._",
                "",
            ]
        )


class OpenAIRefinementClient:
    provider = "OpenAI"

    def __init__(self, api_key: str) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RefinementError("Install optional AI dependencies with: pip install -r requirements-ai.txt") from exc
        self._client = OpenAI(api_key=api_key)

    def complete(self, prompt: str, model: str) -> str:
        response = self._client.responses.create(
            model=model,
            instructions=SYSTEM_PROMPT,
            input=prompt,
            max_output_tokens=1800,
        )
        return extract_openai_text(response)


class AnthropicRefinementClient:
    provider = "Anthropic"

    def __init__(self, api_key: str) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RefinementError("Install optional AI dependencies with: pip install -r requirements-ai.txt") from exc
        self._client = Anthropic(api_key=api_key)

    def complete(self, prompt: str, model: str) -> str:
        message = self._client.messages.create(
            model=model,
            max_tokens=1800,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return extract_anthropic_text(message)


class GeminiRefinementClient:
    provider = "Gemini"

    def __init__(self, api_key: str) -> None:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RefinementError("Install optional AI dependencies with: pip install -r requirements-ai.txt") from exc
        self._client = genai.Client(api_key=api_key)
        self._types = types

    def complete(self, prompt: str, model: str) -> str:
        response = self._client.models.generate_content(
            model=model,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=1800,
                temperature=0.2,
            ),
        )
        return extract_gemini_text(response)


def run_refinement(
    report: AnalysisReport,
    paper_text: str,
    openai_api_key: str,
    anthropic_api_key: str,
    openai_model: str = DEFAULT_OPENAI_MODEL,
    anthropic_model: str = DEFAULT_ANTHROPIC_MODEL,
    openai_client: RefinementClient | None = None,
    anthropic_client: RefinementClient | None = None,
) -> RefinementReport:
    return run_provider_refinement(
        report,
        paper_text,
        critic=ProviderSelection("critic", "OpenAI", openai_model, openai_api_key),
        challenger=ProviderSelection("challenger", "Anthropic", anthropic_model, anthropic_api_key),
        clients={"critic": openai_client, "challenger": anthropic_client},
    )


def run_provider_refinement(
    report: AnalysisReport,
    paper_text: str,
    critic: ProviderSelection,
    challenger: ProviderSelection,
    clients: dict[str, RefinementClient | None] | None = None,
) -> RefinementReport:
    critic = normalize_selection(critic, "critic")
    challenger = normalize_selection(challenger, "challenger")
    clients = clients or {}
    critic_client = resolve_client(critic, clients.get("critic") or clients.get(critic.provider))
    challenger_client = resolve_client(challenger, clients.get("challenger") or clients.get(challenger.provider))
    issue_brief = report.issue_brief or build_issue_brief_from_report(report)
    paper_excerpt = trim_for_prompt(paper_text)

    critic_prompt = build_critic_prompt(report, issue_brief, paper_excerpt)
    critic_response = critic_client.complete(critic_prompt, critic.model)
    critic_turn = ModelTurn(critic_client.provider, critic.model, critic_prompt, critic_response, "complete", "critic")

    challenger_prompt = build_challenger_prompt(report, issue_brief, paper_excerpt, critic_response)
    challenger_response = challenger_client.complete(challenger_prompt, challenger.model)
    challenger_turn = ModelTurn(
        challenger_client.provider,
        challenger.model,
        challenger_prompt,
        challenger_response,
        "complete",
        "challenger",
    )

    disagreements = extract_disagreements(critic_response, challenger_response)
    repair_plan = build_repair_plan(report, critic_turn, challenger_turn, disagreements)
    recheck_report = analyze_paper_text(repair_plan, source_name=f"{report.source_name} repair-plan")
    audit_events = [
        AuditEvent("deterministic brief", "complete", "Issue brief generated from the non-AI report."),
        AuditEvent(
            "critic critique",
            "complete",
            f"{critic.provider} {critic.model} returned a critique and repair plan.",
        ),
        AuditEvent(
            "challenger challenge",
            "complete",
            f"{challenger.provider} {challenger.model} challenged the critique and weak points.",
        ),
        AuditEvent("disagreement extraction", "complete", f"{len(disagreements)} disagreement or tension lines detected."),
        AuditEvent("gauntlet re-check", recheck_report.verdict, "The combined repair plan was sent back through the deterministic rules."),
    ]
    return RefinementReport(
        source_name=report.source_name,
        created_at=utc_now_iso(),
        deterministic_verdict=report.verdict,
        issue_brief=issue_brief,
        critic_turn=critic_turn,
        challenger_turn=challenger_turn,
        disagreements=disagreements,
        repair_plan=repair_plan,
        recheck_report=recheck_report,
        audit_events=audit_events,
    )


def normalize_selection(selection: ProviderSelection, default_role: str) -> ProviderSelection:
    provider = normalize_provider(selection.provider)
    model = selection.model.strip() or DEFAULT_PROVIDER_MODELS[provider]
    role = selection.role.strip().lower() or default_role
    return ProviderSelection(role=role, provider=provider, model=model, api_key=selection.api_key)


def normalize_provider(provider: str) -> str:
    cleaned = provider.strip().lower()
    for known_provider in PROVIDER_ORDER:
        if cleaned == known_provider.lower():
            return known_provider
    raise RefinementError(f"Unknown refinement provider: {provider}. Choose Gemini, OpenAI, or Anthropic.")


def resolve_client(selection: ProviderSelection, injected_client: RefinementClient | None = None) -> RefinementClient:
    if injected_client:
        return injected_client
    if not selection.api_key.strip():
        raise RefinementError(f"{selection.provider} API key is required for the {selection.role} slot.")
    if selection.provider == "OpenAI":
        return OpenAIRefinementClient(selection.api_key)
    if selection.provider == "Anthropic":
        return AnthropicRefinementClient(selection.api_key)
    if selection.provider == "Gemini":
        return GeminiRefinementClient(selection.api_key)
    raise RefinementError(f"Unknown refinement provider: {selection.provider}.")


def build_critic_prompt(report: AnalysisReport, issue_brief: str, paper_excerpt: str) -> str:
    return f"""The Gauntlet deterministic report found the following issues.

SOURCE: {report.source_name}
DETERMINISTIC ISSUE BRIEF:
{issue_brief}

PAPER EXCERPT:
{paper_excerpt}

Produce a visible critique and repair plan. Use exactly these sections:
1. Strongest claims worth preserving
2. Claims that need repair
3. Missing mechanisms
4. Missing evidence or falsifiable checks
5. Concrete repair plan

Do not rewrite the paper. Do not invent citations. Do not expose hidden reasoning."""


def build_challenger_prompt(report: AnalysisReport, issue_brief: str, paper_excerpt: str, critic_response: str) -> str:
    return f"""A first model proposed this critique and repair plan for a paper.

SOURCE: {report.source_name}
DETERMINISTIC ISSUE BRIEF:
{issue_brief}

PAPER EXCERPT:
{paper_excerpt}

FIRST MODEL OUTPUT:
{critic_response}

Challenge the first model. Identify weak repairs, missed contradictions, unsupported assumptions, and anything that still fails The Gauntlet rubric. Then give a corrected repair plan.
Do not rewrite the paper. Do not invent citations. Do not expose hidden reasoning."""


def build_openai_prompt(report: AnalysisReport, issue_brief: str, paper_excerpt: str) -> str:
    return build_critic_prompt(report, issue_brief, paper_excerpt)


def build_anthropic_prompt(report: AnalysisReport, issue_brief: str, paper_excerpt: str, openai_response: str) -> str:
    return build_challenger_prompt(report, issue_brief, paper_excerpt, openai_response)


def build_issue_brief_from_report(report: AnalysisReport) -> str:
    lines = [f"Verdict: {report.verdict}", f"Confidence: {report.confidence:.0%}", report.summary]
    for claim in report.claims[:8]:
        gaps = ", ".join(claim.gaps) if claim.gaps else "none"
        lines.append(f"- {claim.id}: {claim.status}; gaps: {gaps}; repair: {claim.repair_suggestion}")
    for finding in report.findings[:8]:
        lines.append(f"- {finding.id}: {finding.type} ({finding.severity}); {finding.explanation}")
    return "\n".join(lines)


def build_repair_plan(report: AnalysisReport, critic_turn: ModelTurn, challenger_turn: ModelTurn, disagreements: list[str]) -> str:
    unresolved = "\n".join(f"- {item}" for item in disagreements) if disagreements else "- No explicit model disagreement was extracted."
    weak_claims = "\n".join(
        f"- {claim.id}: {claim.repair_suggestion}" for claim in report.claims if claim.status != "resolved"
    ) or "- Preserve current claim structure while keeping evidence and mechanism links explicit."
    return f"""The Gauntlet repair plan explains how the paper can address the deterministic findings through explicit mechanisms, evidence links, and scope boundaries.

Claim-level repairs:
{weak_claims}

Model critique synthesis:
- {critic_turn.provider} critique summary: {summarize_text(critic_turn.response)}
- {challenger_turn.provider} challenge summary: {summarize_text(challenger_turn.response)}

Remaining disagreements or unresolved tension:
{unresolved}

Required revision barriers:
1. Each resolution claim must name the exact paradox, contradiction, anomaly, or problem it resolves.
2. Each claim must include a mechanism through a named process, derivation, proof, equation, or causal bridge.
3. Each mechanism must link to evidence such as a citation, measurement, formal derivation, reproducible test, or falsifiable prediction.
4. Any universal claim must include scope boundaries and exceptions.
5. Theory-as-fact wording must be replaced with evidence-based language.
"""


def extract_disagreements(openai_response: str, anthropic_response: str) -> list[str]:
    combined = f"{openai_response}\n{anthropic_response}"
    lines = [line.strip(" -*\t") for line in combined.splitlines()]
    indicators = ("disagree", "missed", "still", "unresolved", "weak", "unsupported", "contradiction", "assumption")
    extracted = []
    for line in lines:
        if 20 <= len(line) <= 260 and any(indicator in line.lower() for indicator in indicators):
            extracted.append(line)
    return dedupe_preserve_order(extracted)[:8]


def extract_openai_text(response) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text).strip()
    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(str(text))
    text = "\n".join(chunks).strip()
    return text or str(response)


def extract_anthropic_text(message) -> str:
    chunks = []
    for item in getattr(message, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            chunks.append(str(text))
    text = "\n".join(chunks).strip()
    return text or str(message)


def extract_gemini_text(response) -> str:
    direct_text = getattr(response, "text", None)
    if direct_text:
        return str(direct_text).strip()
    chunks: list[str] = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            text = getattr(part, "text", None)
            if text:
                chunks.append(str(text))
    text = "\n".join(chunks).strip()
    return text or str(response)


def trim_for_prompt(text: str, limit: int = 12000) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    head = text[: int(limit * 0.62)].strip()
    tail = text[-int(limit * 0.28) :].strip()
    return f"{head}\n\n[...middle omitted for prompt length...]\n\n{tail}"


def summarize_text(text: str, limit: int = 360) -> str:
    return trim_sentence(re.sub(r"\s+", " ", text).strip(), limit)


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        key = re.sub(r"\W+", " ", item.lower()).strip()
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped
