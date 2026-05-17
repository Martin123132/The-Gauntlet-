from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Literal


Verdict = Literal["RESOLVES", "PARTIAL", "FAILS", "CREATES_NEW_PARADOXES"]
Severity = Literal["low", "medium", "high"]
ClaimStatus = Literal["resolved", "partial", "failed"]


@dataclass(frozen=True)
class SourceSpan:
    anchor_id: str
    section: str
    sentence_index: int
    page_number: int | None
    char_start: int
    char_end: int
    text: str


@dataclass(frozen=True)
class EvidenceLink:
    id: str
    type: str
    snippet: str
    section: str
    sentence_index: int
    confidence: float
    source_span: SourceSpan | None = None


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
    source_span: SourceSpan | None = None
    related_source_span: SourceSpan | None = None


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
    source_span: SourceSpan | None = None


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
    source_spans: list[SourceSpan] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisReport":
        return cls(
            source_name=data.get("source_name", "paper"),
            verdict=data.get("verdict", "FAILS"),
            confidence=float(data.get("confidence", 0.0)),
            created_at=data.get("created_at", utc_now_iso()),
            word_count=int(data.get("word_count", 0)),
            sentence_count=int(data.get("sentence_count", 0)),
            claims=[claim_result_from_dict(item) for item in data.get("claims", [])],
            findings=[finding_from_dict(item) for item in data.get("findings", [])],
            evidence=evidence_profile_from_dict(data.get("evidence", {})),
            summary=data.get("summary", ""),
            sections=list(data.get("sections", [])),
            audit_events=[audit_event_from_dict(item) for item in data.get("audit_events", [])],
            verdict_rubric=[rubric_score_from_dict(item) for item in data.get("verdict_rubric", [])],
            issue_brief=data.get("issue_brief", ""),
            source_spans=[source_span_from_dict(item) for item in data.get("source_spans", []) if item],
        )

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
                source = source_reference(claim.source_span)
                lines.extend(
                    [
                        f"### {claim.id or 'Claim'} - {claim.status.title()}",
                        "",
                        claim.claim,
                        "",
                        f"- Source: {source}",
                        f"- Quality: {claim.quality:.2f}",
                        f"- Evidence strength: {claim.evidence_strength:.2f}",
                        f"- Mechanism: {claim.mechanism}",
                        f"- Gaps: {gaps}",
                        f"- Evidence links: {links}",
                        f"- Repair: {claim.repair_suggestion or 'No immediate repair suggested.'}",
                        "",
                    ]
                )
                if claim.source_span:
                    lines.extend([f"> Source text: {claim.source_span.text}", ""])
        else:
            lines.extend(["No clear resolution claims were detected.", ""])

        lines.extend(["## Findings", ""])
        if self.findings:
            for finding in self.findings:
                source = source_reference(finding.source_span)
                lines.extend(
                    [
                        f"### {finding.id or 'Finding'} - {finding.type} ({finding.severity})",
                        "",
                        f"> {finding.sentence}",
                        "",
                        f"- Source: {source}",
                        f"- Trigger: {finding.trigger or 'rule match'}",
                        f"- Explanation: {finding.explanation}",
                        f"- Repair suggestion: {finding.repair_suggestion}",
                        f"- Confidence: {finding.confidence:.0%}",
                        "",
                    ]
                )
                if finding.related_source_span:
                    lines.extend([f"- Related source: {source_reference(finding.related_source_span)}", ""])
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
                "### Evidence Snippets",
                "",
            ]
        )
        if self.evidence.evidence_links:
            for link in self.evidence.evidence_links:
                lines.extend(
                    [
                        f"- {link.id} ({link.type}): {source_reference(link.source_span)}",
                        f"  - {link.snippet}",
                    ]
                )
        else:
            lines.append("- No evidence snippets were indexed.")

        lines.extend(
            [
                "",
                "## Source Trace",
                "",
            ]
        )
        if self.source_spans:
            for span in self.source_spans[:40]:
                lines.append(f"- {span.anchor_id}: {source_reference(span)}")
        else:
            lines.append("- No source trace was recorded.")

        lines.extend(
            [
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


def source_span_from_dict(data: SourceSpan | dict[str, Any] | None) -> SourceSpan | None:
    if data is None or isinstance(data, SourceSpan):
        return data
    return SourceSpan(
        anchor_id=data.get("anchor_id", ""),
        section=data.get("section", "Document"),
        sentence_index=int(data.get("sentence_index", 0)),
        page_number=data.get("page_number"),
        char_start=int(data.get("char_start", -1)),
        char_end=int(data.get("char_end", -1)),
        text=data.get("text", ""),
    )


def evidence_link_from_dict(data: EvidenceLink | dict[str, Any]) -> EvidenceLink:
    if isinstance(data, EvidenceLink):
        return data
    return EvidenceLink(
        id=data.get("id", ""),
        type=data.get("type", ""),
        snippet=data.get("snippet", ""),
        section=data.get("section", "Document"),
        sentence_index=int(data.get("sentence_index", 0)),
        confidence=float(data.get("confidence", 0.0)),
        source_span=source_span_from_dict(data.get("source_span")),
    )


def rubric_score_from_dict(data: RubricScore | dict[str, Any]) -> RubricScore:
    if isinstance(data, RubricScore):
        return data
    return RubricScore(
        name=data.get("name", ""),
        score=float(data.get("score", 0.0)),
        weight=float(data.get("weight", 0.0)),
        reason=data.get("reason", ""),
    )


def audit_event_from_dict(data: AuditEvent | dict[str, Any]) -> AuditEvent:
    if isinstance(data, AuditEvent):
        return data
    raw_score = data.get("score")
    return AuditEvent(
        step=data.get("step", ""),
        status=data.get("status", ""),
        detail=data.get("detail", ""),
        score=None if raw_score is None else float(raw_score),
    )


def finding_from_dict(data: Finding | dict[str, Any]) -> Finding:
    if isinstance(data, Finding):
        return data
    return Finding(
        type=data.get("type", ""),
        severity=data.get("severity", "low"),
        sentence=data.get("sentence", ""),
        explanation=data.get("explanation", ""),
        repair_suggestion=data.get("repair_suggestion", ""),
        confidence=float(data.get("confidence", 0.0)),
        related_sentence=data.get("related_sentence"),
        id=data.get("id", ""),
        section=data.get("section", "Document"),
        trigger=data.get("trigger", ""),
        claim_id=data.get("claim_id"),
        source_span=source_span_from_dict(data.get("source_span")),
        related_source_span=source_span_from_dict(data.get("related_source_span")),
    )


def claim_result_from_dict(data: ClaimResult | dict[str, Any]) -> ClaimResult:
    if isinstance(data, ClaimResult):
        return data
    return ClaimResult(
        claim=data.get("claim", ""),
        status=data.get("status", "failed"),
        quality=float(data.get("quality", 0.0)),
        mechanism=data.get("mechanism", ""),
        evidence_strength=float(data.get("evidence_strength", 0.0)),
        gaps=list(data.get("gaps", [])),
        id=data.get("id", ""),
        section=data.get("section", "Document"),
        sentence_index=int(data.get("sentence_index", 0)),
        evidence_links=[evidence_link_from_dict(item) for item in data.get("evidence_links", [])],
        rubric_scores=[rubric_score_from_dict(item) for item in data.get("rubric_scores", [])],
        audit_events=[audit_event_from_dict(item) for item in data.get("audit_events", [])],
        repair_suggestion=data.get("repair_suggestion", ""),
        trigger_terms=list(data.get("trigger_terms", [])),
        source_span=source_span_from_dict(data.get("source_span")),
    )


def evidence_profile_from_dict(data: EvidenceProfile | dict[str, Any]) -> EvidenceProfile:
    if isinstance(data, EvidenceProfile):
        return data
    return EvidenceProfile(
        score=float(data.get("score", 0.0)),
        quantitative_evidence=int(data.get("quantitative_evidence", 0)),
        mathematical_content=int(data.get("mathematical_content", 0)),
        citations=int(data.get("citations", 0)),
        methodology_terms=int(data.get("methodology_terms", 0)),
        evidence_terms=int(data.get("evidence_terms", 0)),
        linked_evidence=int(data.get("linked_evidence", 0)),
        section_counts=dict(data.get("section_counts", {})),
        evidence_links=[evidence_link_from_dict(item) for item in data.get("evidence_links", [])],
    )


def analysis_report_from_dict(data: AnalysisReport | dict[str, Any]) -> AnalysisReport:
    if isinstance(data, AnalysisReport):
        return data
    return AnalysisReport.from_dict(data)


def source_reference(span: SourceSpan | None) -> str:
    if not span:
        return "Source unavailable"
    parts: list[str] = []
    if span.page_number is not None:
        parts.append(f"Page {span.page_number}")
    parts.append(span.section or "Document")
    parts.append(f"sentence {span.sentence_index}")
    if span.char_start >= 0 and span.char_end >= span.char_start:
        parts.append(f"chars {span.char_start}-{span.char_end}")
    return ", ".join(parts)
