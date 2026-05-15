from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Literal


Verdict = Literal["RESOLVES", "PARTIAL", "FAILS", "CREATES_NEW_PARADOXES"]
Severity = Literal["low", "medium", "high"]
ClaimStatus = Literal["resolved", "partial", "failed"]


@dataclass(frozen=True)
class EvidenceLink:
    id: str
    type: str
    snippet: str
    section: str
    sentence_index: int
    confidence: float


@dataclass(frozen=True)
class RubricScore:
    name: str
    score: float
    weight: float
    reason: str


@dataclass(frozen=True)
class AuditEvent:
    step: str
    status: str
    detail: str
    score: float | None = None


@dataclass(frozen=True)
class Finding:
    type: str
    severity: Severity
    sentence: str
    explanation: str
    repair_suggestion: str
    confidence: float
    related_sentence: str | None = None
    id: str = ""
    section: str = "Document"
    trigger: str = ""
    claim_id: str | None = None


@dataclass(frozen=True)
class ClaimResult:
    claim: str
    status: ClaimStatus
    quality: float
    mechanism: str
    evidence_strength: float
    gaps: list[str]
    id: str = ""
    section: str = "Document"
    sentence_index: int = 0
    evidence_links: list[EvidenceLink] = field(default_factory=list)
    rubric_scores: list[RubricScore] = field(default_factory=list)
    audit_events: list[AuditEvent] = field(default_factory=list)
    repair_suggestion: str = ""
    trigger_terms: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvidenceProfile:
    score: float
    quantitative_evidence: int
    mathematical_content: int
    citations: int
    methodology_terms: int
    evidence_terms: int
    linked_evidence: int = 0
    section_counts: dict[str, int] = field(default_factory=dict)
    evidence_links: list[EvidenceLink] = field(default_factory=list)


@dataclass(frozen=True)
class AnalysisReport:
    source_name: str
    verdict: Verdict
    confidence: float
    created_at: str
    word_count: int
    sentence_count: int
    claims: list[ClaimResult]
    findings: list[Finding]
    evidence: EvidenceProfile
    summary: str
    sections: list[str] = field(default_factory=list)
    audit_events: list[AuditEvent] = field(default_factory=list)
    verdict_rubric: list[RubricScore] = field(default_factory=list)
    issue_brief: str = ""

    @property
    def resolved_claims(self) -> int:
        return sum(1 for claim in self.claims if claim.status == "resolved")

    @property
    def partial_claims(self) -> int:
        return sum(1 for claim in self.claims if claim.status == "partial")

    @property
    def failed_claims(self) -> int:
        return sum(1 for claim in self.claims if claim.status == "failed")

    @property
    def high_severity_findings(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "high")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_markdown(self) -> str:
        lines = [
            f"# The Gauntlet Report: {self.source_name}",
            "",
            f"- Verdict: **{self.verdict}**",
            f"- Confidence: **{self.confidence:.0%}**",
            f"- Evidence quality: **{self.evidence.score:.2f}/1.00**",
            f"- Claims: **{len(self.claims)} total** "
            f"({self.resolved_claims} resolved, {self.partial_claims} partial, {self.failed_claims} failed)",
            f"- Findings: **{len(self.findings)}** ({self.high_severity_findings} high severity)",
            f"- Sections: **{', '.join(self.sections) if self.sections else 'Document'}**",
            f"- Generated: {self.created_at}",
            "",
            "## Summary",
            "",
            self.summary,
            "",
            "## Claims",
            "",
        ]

        if self.claims:
            for claim in self.claims:
                gaps = ", ".join(claim.gaps) if claim.gaps else "none"
                links = ", ".join(link.id for link in claim.evidence_links) if claim.evidence_links else "none"
                lines.extend(
                    [
                        f"### {claim.id or 'Claim'} - {claim.status.title()}",
                        "",
                        claim.claim,
                        "",
                        f"- Section: {claim.section}",
                        f"- Quality: {claim.quality:.2f}",
                        f"- Evidence strength: {claim.evidence_strength:.2f}",
                        f"- Mechanism: {claim.mechanism}",
                        f"- Gaps: {gaps}",
                        f"- Evidence links: {links}",
                        f"- Repair: {claim.repair_suggestion or 'No immediate repair suggested.'}",
                        "",
                    ]
                )
        else:
            lines.extend(["No clear resolution claims were detected.", ""])

        lines.extend(["## Findings", ""])
        if self.findings:
            for finding in self.findings:
                lines.extend(
                    [
                        f"### {finding.id or 'Finding'} - {finding.type} ({finding.severity})",
                        "",
                        f"> {finding.sentence}",
                        "",
                        f"- Section: {finding.section}",
                        f"- Trigger: {finding.trigger or 'rule match'}",
                        f"- Explanation: {finding.explanation}",
                        f"- Repair suggestion: {finding.repair_suggestion}",
                        f"- Confidence: {finding.confidence:.0%}",
                        "",
                    ]
                )
        else:
            lines.extend(["No internal contradictions were detected by the rule set.", ""])

        lines.extend(
            [
                "## Evidence Profile",
                "",
                f"- Quantitative evidence: {self.evidence.quantitative_evidence}",
                f"- Mathematical content: {self.evidence.mathematical_content}",
                f"- Citations: {self.evidence.citations}",
                f"- Methodology terms: {self.evidence.methodology_terms}",
                f"- Evidence terms: {self.evidence.evidence_terms}",
                f"- Linked evidence snippets: {self.evidence.linked_evidence}",
                "",
                "## Verdict Rubric",
                "",
            ]
        )
        if self.verdict_rubric:
            for score in self.verdict_rubric:
                lines.append(f"- {score.name}: {score.score:.2f} x {score.weight:.2f} - {score.reason}")
        else:
            lines.append("- No rubric details were recorded.")

        lines.extend(
            [
                "",
                "## Issue Brief",
                "",
                self.issue_brief or "No issue brief was generated.",
                "",
                "_This report was produced by deterministic rules only. No AI model or API was used._",
                "",
            ]
        )
        return "\n".join(lines)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
