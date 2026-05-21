from __future__ import annotations

from dataclasses import dataclass

from .models import AnalysisReport, ClaimResult, EvidenceLink, SourceSpan, source_reference


USABLE_EVIDENCE_THRESHOLD = 0.42
STRONG_EVIDENCE_THRESHOLD = 0.60


@dataclass(frozen=True)
class ClaimEvidenceRow:
    claim_id: str
    claim: str
    claim_status: str
    coverage: str
    priority: str
    evidence_strength: float
    evidence_count: int
    usable_evidence_count: int
    strong_evidence_count: int
    gaps: tuple[str, ...]
    source_span: SourceSpan | None
    evidence_links: tuple[EvidenceLink, ...]
    repair_suggestion: str


@dataclass(frozen=True)
class ClaimEvidenceMap:
    rows: tuple[ClaimEvidenceRow, ...]
    orphan_evidence_links: tuple[EvidenceLink, ...]
    claims_with_evidence: int
    claims_with_usable_evidence: int
    claims_with_strong_evidence: int


def build_claim_evidence_map(report: AnalysisReport) -> ClaimEvidenceMap:
    rows = tuple(claim_evidence_row(claim, index) for index, claim in enumerate(report.claims, start=1))
    linked_ids = {link.id for row in rows for link in row.evidence_links}
    orphan_links = tuple(link for link in report.evidence.evidence_links if link.id not in linked_ids)
    return ClaimEvidenceMap(
        rows=tuple(sorted(rows, key=claim_evidence_sort_key)),
        orphan_evidence_links=orphan_links,
        claims_with_evidence=sum(1 for row in rows if row.evidence_count > 0),
        claims_with_usable_evidence=sum(1 for row in rows if row.usable_evidence_count > 0),
        claims_with_strong_evidence=sum(1 for row in rows if row.strong_evidence_count > 0),
    )


def claim_evidence_map_to_markdown(
    report: AnalysisReport,
    evidence_map: ClaimEvidenceMap | None = None,
) -> str:
    claim_map = evidence_map or build_claim_evidence_map(report)
    lines = [
        f"# Claim-Evidence Map: {report.source_name}",
        "",
        f"- Verdict: **{report.verdict}**",
        f"- Claims: **{len(claim_map.rows)}**",
        f"- Claims with evidence: **{claim_map.claims_with_evidence}**",
        f"- Claims with usable evidence: **{claim_map.claims_with_usable_evidence}**",
        f"- Claims with strong evidence: **{claim_map.claims_with_strong_evidence}**",
        f"- Orphan evidence snippets: **{len(claim_map.orphan_evidence_links)}**",
        "",
    ]
    if not claim_map.rows:
        lines.extend(["No clear claims were detected, so no claim-evidence rows were generated.", ""])
    for row in claim_map.rows:
        lines.extend(
            [
                f"## {row.claim_id} - {row.coverage.title()}",
                "",
                row.claim,
                "",
                f"- Claim status: {row.claim_status}",
                f"- Priority: {row.priority}",
                f"- Source: {source_reference(row.source_span)}",
                f"- Evidence strength: {row.evidence_strength:.2f}",
                f"- Evidence links: {row.evidence_count} total, {row.usable_evidence_count} usable, {row.strong_evidence_count} strong",
                f"- Gaps: {', '.join(row.gaps) if row.gaps else 'none'}",
                f"- Repair: {row.repair_suggestion}",
                "",
            ]
        )
        if row.source_span:
            lines.extend([f"> Claim source: {row.source_span.text}", ""])
        if row.evidence_links:
            lines.extend(["### Linked Evidence", ""])
            for link in row.evidence_links:
                lines.extend(
                    [
                        f"- {link.id} ({link.type}, confidence {link.confidence:.0%}): {source_reference(link.source_span)}",
                        f"  - {link.snippet}",
                    ]
                )
            lines.append("")
        else:
            lines.extend(["No evidence snippets are linked to this claim.", ""])

    if claim_map.orphan_evidence_links:
        lines.extend(["## Orphan Evidence", ""])
        for link in claim_map.orphan_evidence_links:
            lines.extend(
                [
                    f"- {link.id} ({link.type}, confidence {link.confidence:.0%}): {source_reference(link.source_span)}",
                    f"  - {link.snippet}",
                ]
            )
        lines.append("")

    lines.extend(
        [
            "_Claim-Evidence Map exports contain claim text, linked evidence snippets, source references, and repair suggestions only. They do not include the full uploaded paper file._",
            "",
        ]
    )
    return "\n".join(lines)


def claim_evidence_row(claim: ClaimResult, fallback_index: int) -> ClaimEvidenceRow:
    links = tuple(claim.evidence_links)
    usable_count = sum(1 for link in links if link.confidence >= USABLE_EVIDENCE_THRESHOLD)
    strong_count = sum(1 for link in links if link.confidence >= STRONG_EVIDENCE_THRESHOLD)
    coverage = classify_coverage(claim, links, usable_count, strong_count)
    return ClaimEvidenceRow(
        claim_id=claim.id or f"C{fallback_index}",
        claim=claim.claim,
        claim_status=claim.status,
        coverage=coverage,
        priority=coverage_priority(coverage, claim.status),
        evidence_strength=claim.evidence_strength,
        evidence_count=len(links),
        usable_evidence_count=usable_count,
        strong_evidence_count=strong_count,
        gaps=tuple(claim.gaps),
        source_span=claim.source_span,
        evidence_links=links,
        repair_suggestion=repair_suggestion_for_coverage(claim, coverage),
    )


def classify_coverage(
    claim: ClaimResult,
    links: tuple[EvidenceLink, ...],
    usable_count: int,
    strong_count: int,
) -> str:
    if strong_count and claim.status == "resolved":
        return "strong"
    if usable_count:
        return "linked"
    if links:
        return "weak"
    return "missing"


def coverage_priority(coverage: str, claim_status: str) -> str:
    if coverage == "missing" or claim_status == "failed":
        return "high"
    if coverage == "weak" or claim_status == "partial":
        return "medium"
    return "low"


def repair_suggestion_for_coverage(claim: ClaimResult, coverage: str) -> str:
    if claim.repair_suggestion:
        return claim.repair_suggestion
    if coverage == "missing":
        return "Add a nearby citation, measurement, derivation, method detail, or falsifiable test that directly supports this claim."
    if coverage == "weak":
        return "Move stronger evidence closer to the claim or make the current evidence more specific."
    if coverage == "linked":
        return "Keep the evidence link visible and clarify why it supports this claim."
    return "Preserve the strong claim-evidence link while tightening scope and mechanism language."


def claim_evidence_sort_key(row: ClaimEvidenceRow) -> tuple[int, int, str]:
    priority_order = {"high": 0, "medium": 1, "low": 2}
    coverage_order = {"missing": 0, "weak": 1, "linked": 2, "strong": 3}
    return (priority_order.get(row.priority, 3), coverage_order.get(row.coverage, 4), row.claim_id)
