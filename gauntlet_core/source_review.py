from __future__ import annotations

from dataclasses import dataclass

from .action_plan import build_reviewer_action_plan
from .models import AnalysisReport, SourceSpan, source_reference


@dataclass(frozen=True)
class SourceReviewItem:
    id: str
    kind: str
    title: str
    priority: int
    severity: str
    status: str
    source_span: SourceSpan | None
    related_source_span: SourceSpan | None
    body: str
    explanation: str
    repair_suggestion: str


def build_source_review_items(report: AnalysisReport) -> list[SourceReviewItem]:
    items: list[SourceReviewItem] = []

    for finding in report.findings:
        items.append(
            SourceReviewItem(
                id=finding.id or f"F{len(items) + 1}",
                kind="Finding",
                title=finding.type,
                priority=finding_priority(finding.severity),
                severity=finding.severity,
                status=finding.severity,
                source_span=finding.source_span,
                related_source_span=finding.related_source_span,
                body=finding.sentence,
                explanation=finding.explanation,
                repair_suggestion=finding.repair_suggestion,
            )
        )

    for claim in report.claims:
        if claim.status not in {"failed", "partial"}:
            continue
        gap_text = ", ".join(claim.gaps) if claim.gaps else "claim support did not satisfy the rubric"
        items.append(
            SourceReviewItem(
                id=claim.id or f"C{len(items) + 1}",
                kind="Claim",
                title=f"{claim.status.title()} claim",
                priority=10 if claim.status == "failed" else 20,
                severity="high" if claim.status == "failed" else "medium",
                status=claim.status,
                source_span=claim.source_span,
                related_source_span=None,
                body=claim.claim,
                explanation=f"Claim gaps: {gap_text}.",
                repair_suggestion=claim.repair_suggestion or "Tie the claim to mechanism, evidence, and scope.",
            )
        )

    for link in report.evidence.evidence_links:
        weak = link.confidence < 0.6
        items.append(
            SourceReviewItem(
                id=link.id,
                kind="Evidence",
                title="Weak evidence link" if weak else "Supporting evidence",
                priority=25 if weak else 80,
                severity="medium" if weak else "low",
                status="weak" if weak else "supporting",
                source_span=link.source_span,
                related_source_span=None,
                body=link.snippet,
                explanation=f"Evidence type: {link.type}. Link confidence: {link.confidence:.0%}.",
                repair_suggestion=(
                    "Move stronger evidence, citation, measurement, or method detail next to the claim it supports."
                    if weak
                    else "Keep this evidence close to the claim it supports."
                ),
            )
        )

    for action in build_reviewer_action_plan(report):
        items.append(
            SourceReviewItem(
                id=action.id,
                kind="Repair",
                title=action.title,
                priority=35 + action_priority_offset(action.priority),
                severity=action.priority,
                status="needs repair",
                source_span=action.source_span,
                related_source_span=None,
                body=action.detail,
                explanation=f"{action.category} repair targeting {action.target}.",
                repair_suggestion=action.suggested_fix,
            )
        )

    return sorted(deduplicate_source_review_items(items), key=source_review_sort_key)


def source_review_to_markdown(report: AnalysisReport, items: list[SourceReviewItem] | None = None) -> str:
    review_items = items if items is not None else build_source_review_items(report)
    lines = [
        f"# Source Review: {report.source_name}",
        "",
        f"- Verdict: **{report.verdict}**",
        f"- Confidence: **{report.confidence:.0%}**",
        f"- Source review items: **{len(review_items)}**",
        "",
    ]
    if not review_items:
        lines.extend(["No source review items were generated.", ""])
        return "\n".join(lines)

    for item in review_items:
        lines.extend(
            [
                f"## {item.id} - {item.title}",
                "",
                f"- Kind: {item.kind}",
                f"- Priority: {item.priority}",
                f"- Severity: {item.severity}",
                f"- Status: {item.status}",
                f"- Source: {source_reference(item.source_span)}",
            ]
        )
        if item.related_source_span:
            lines.append(f"- Related source: {source_reference(item.related_source_span)}")
        lines.extend(
            [
                f"- Issue: {item.body}",
                f"- Why it matters: {item.explanation}",
                f"- Repair: {item.repair_suggestion}",
                "",
            ]
        )
        if item.source_span:
            lines.extend([f"> Source text: {item.source_span.text}", ""])
        if item.related_source_span:
            lines.extend([f"> Related source text: {item.related_source_span.text}", ""])
    lines.extend(
        [
            "_Source Review exports contain source references, snippets, and repair notes only. They do not include the full uploaded paper file._",
            "",
        ]
    )
    return "\n".join(lines)


def finding_priority(severity: str) -> int:
    return {"high": 0, "medium": 50, "low": 70}.get(severity, 75)


def action_priority_offset(priority: str) -> int:
    return {"high": 0, "medium": 5, "low": 10}.get(priority, 10)


def source_review_sort_key(item: SourceReviewItem) -> tuple[int, int, str]:
    severity_order = {"high": 0, "medium": 1, "low": 2}
    return (item.priority, severity_order.get(item.severity, 3), item.id)


def deduplicate_source_review_items(items: list[SourceReviewItem]) -> list[SourceReviewItem]:
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[SourceReviewItem] = []
    for item in items:
        key = (
            item.kind,
            item.title,
            item.body,
            item.source_span.anchor_id if item.source_span else "",
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
