from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Protocol

from .analysis import analyze_paper_text, trim_sentence
from .models import AnalysisReport, AuditEvent, utc_now_iso


DEFAULT_OPENAI_MODEL = "gpt-4.1"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"

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
class ModelTurn:
    provider: str
    model: str
    prompt: str
    response: str
    status: str


@dataclass(frozen=True)
class RefinementReport:
    source_name: str
    created_at: str
    deterministic_verdict: str
    issue_brief: str
    openai_turn: ModelTurn
    anthropic_turn: ModelTurn
    disagreements: list[str]
    repair_plan: str
    recheck_report: AnalysisReport
    audit_events: list[AuditEvent]

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
                "## OpenAI Critique",
                "",
                self.openai_turn.response,
                "",
                "## Anthropic Challenge",
                "",
                self.anthropic_turn.response,
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
    if not openai_client and not openai_api_key.strip():
        raise RefinementError("OpenAI API key is required for the optional refinement chamber.")
    if not anthropic_client and not anthropic_api_key.strip():
        raise RefinementError("Anthropic API key is required for the optional refinement chamber.")

    openai_client = openai_client or OpenAIRefinementClient(openai_api_key)
    anthropic_client = anthropic_client or AnthropicRefinementClient(anthropic_api_key)
    issue_brief = report.issue_brief or build_issue_brief_from_report(report)
    paper_excerpt = trim_for_prompt(paper_text)

    openai_prompt = build_openai_prompt(report, issue_brief, paper_excerpt)
    openai_response = openai_client.complete(openai_prompt, openai_model)
    openai_turn = ModelTurn(openai_client.provider, openai_model, openai_prompt, openai_response, "complete")

    anthropic_prompt = build_anthropic_prompt(report, issue_brief, paper_excerpt, openai_response)
    anthropic_response = anthropic_client.complete(anthropic_prompt, anthropic_model)
    anthropic_turn = ModelTurn(anthropic_client.provider, anthropic_model, anthropic_prompt, anthropic_response, "complete")

    disagreements = extract_disagreements(openai_response, anthropic_response)
    repair_plan = build_repair_plan(report, openai_response, anthropic_response, disagreements)
    recheck_report = analyze_paper_text(repair_plan, source_name=f"{report.source_name} repair-plan")
    audit_events = [
        AuditEvent("deterministic brief", "complete", "Issue brief generated from the non-AI report."),
        AuditEvent("openai critique", "complete", f"{openai_model} returned a critique and repair plan."),
        AuditEvent("anthropic challenge", "complete", f"{anthropic_model} challenged the critique and weak points."),
        AuditEvent("disagreement extraction", "complete", f"{len(disagreements)} disagreement or tension lines detected."),
        AuditEvent("gauntlet re-check", recheck_report.verdict, "The combined repair plan was sent back through the deterministic rules."),
    ]
    return RefinementReport(
        source_name=report.source_name,
        created_at=utc_now_iso(),
        deterministic_verdict=report.verdict,
        issue_brief=issue_brief,
        openai_turn=openai_turn,
        anthropic_turn=anthropic_turn,
        disagreements=disagreements,
        repair_plan=repair_plan,
        recheck_report=recheck_report,
        audit_events=audit_events,
    )


def build_openai_prompt(report: AnalysisReport, issue_brief: str, paper_excerpt: str) -> str:
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


def build_anthropic_prompt(report: AnalysisReport, issue_brief: str, paper_excerpt: str, openai_response: str) -> str:
    return f"""A first model proposed this critique and repair plan for a paper.

SOURCE: {report.source_name}
DETERMINISTIC ISSUE BRIEF:
{issue_brief}

PAPER EXCERPT:
{paper_excerpt}

FIRST MODEL OUTPUT:
{openai_response}

Challenge the first model. Identify weak repairs, missed contradictions, unsupported assumptions, and anything that still fails The Gauntlet rubric. Then give a corrected repair plan.
Do not rewrite the paper. Do not invent citations. Do not expose hidden reasoning."""


def build_issue_brief_from_report(report: AnalysisReport) -> str:
    lines = [f"Verdict: {report.verdict}", f"Confidence: {report.confidence:.0%}", report.summary]
    for claim in report.claims[:8]:
        gaps = ", ".join(claim.gaps) if claim.gaps else "none"
        lines.append(f"- {claim.id}: {claim.status}; gaps: {gaps}; repair: {claim.repair_suggestion}")
    for finding in report.findings[:8]:
        lines.append(f"- {finding.id}: {finding.type} ({finding.severity}); {finding.explanation}")
    return "\n".join(lines)


def build_repair_plan(
    report: AnalysisReport, openai_response: str, anthropic_response: str, disagreements: list[str]
) -> str:
    unresolved = "\n".join(f"- {item}" for item in disagreements) if disagreements else "- No explicit model disagreement was extracted."
    weak_claims = "\n".join(
        f"- {claim.id}: {claim.repair_suggestion}" for claim in report.claims if claim.status != "resolved"
    ) or "- Preserve current claim structure while keeping evidence and mechanism links explicit."
    return f"""The Gauntlet repair plan explains how the paper can address the deterministic findings through explicit mechanisms, evidence links, and scope boundaries.

Claim-level repairs:
{weak_claims}

Model critique synthesis:
- OpenAI critique summary: {summarize_text(openai_response)}
- Anthropic challenge summary: {summarize_text(anthropic_response)}

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
