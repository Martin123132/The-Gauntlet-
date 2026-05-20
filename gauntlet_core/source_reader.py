from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import AnalysisReport, SourceSpan, source_reference
from .repair_workshop import build_repair_steps
from .revision_recheck import normalize_revision_rechecks, revision_status_label
from .source_review import SourceReviewItem, build_source_review_items


@dataclass(frozen=True)
class SourceReaderAnchor:
    anchor_id: str
    reference: str
    section: str
    page_number: int | None
    sentence_index: int
    text: str
    is_match: bool
    related_count: int


@dataclass(frozen=True)
class SourceReaderRelatedItem:
    id: str
    kind: str
    title: str
    status: str
    source_span: SourceSpan | None
    related_source_span: SourceSpan | None
    body: str
    explanation: str
    repair_suggestion: str


@dataclass(frozen=True)
class SourceReaderView:
    source_name: str
    selected_anchor: str
    selected_span: SourceSpan | None
    context_spans: list[SourceSpan]
    matching_anchors: list[SourceReaderAnchor]
    related_items: list[SourceReaderRelatedItem]
    query: str = ""
    section_filter: str | None = None
    page_filter: int | None = None


def build_source_reader_view(
    report: AnalysisReport,
    selected_anchor: str | None = None,
    query: str = "",
    filters: dict[str, Any] | None = None,
) -> SourceReaderView:
    filters = filters or {}
    source_spans = list(report.source_spans or [])
    if not source_spans:
        return SourceReaderView(
            source_name=report.source_name,
            selected_anchor="",
            selected_span=None,
            context_spans=[],
            matching_anchors=[],
            related_items=[],
            query=clean_query(query),
            section_filter=normalize_section_filter(filters.get("section")),
            page_filter=normalize_page_filter(filters.get("page")),
        )

    normalized_query = clean_query(query)
    section_filter = normalize_section_filter(filters.get("section"))
    page_filter = normalize_page_filter(filters.get("page"))
    matching_spans = [
        span
        for span in source_spans
        if source_span_matches(span, normalized_query, section_filter, page_filter)
    ]
    anchors_by_id = {span.anchor_id: span for span in source_spans}

    if selected_anchor and selected_anchor in anchors_by_id:
        selected_span = anchors_by_id[selected_anchor]
    elif matching_spans:
        selected_span = matching_spans[0]
    else:
        selected_span = source_spans[0]

    all_related_items = build_reader_related_items(
        report,
        repair_progress=filters.get("repair_progress"),
        revision_rechecks=filters.get("revision_rechecks"),
    )
    related_counts = count_related_items_by_anchor(all_related_items)
    matching_anchor_ids = {span.anchor_id for span in matching_spans}
    matching_anchors = [
        SourceReaderAnchor(
            anchor_id=span.anchor_id,
            reference=source_reference(span),
            section=span.section or "Document",
            page_number=span.page_number,
            sentence_index=span.sentence_index,
            text=span.text,
            is_match=span.anchor_id in matching_anchor_ids,
            related_count=related_counts.get(span.anchor_id, 0),
        )
        for span in matching_spans
    ]
    related_items = [
        item
        for item in all_related_items
        if same_anchor(item.source_span, selected_span.anchor_id)
        or same_anchor(item.related_source_span, selected_span.anchor_id)
    ]
    context_spans = build_context_spans(source_spans, selected_span, radius=int(filters.get("context_radius", 2)))
    return SourceReaderView(
        source_name=report.source_name,
        selected_anchor=selected_span.anchor_id,
        selected_span=selected_span,
        context_spans=context_spans,
        matching_anchors=matching_anchors,
        related_items=related_items,
        query=normalized_query,
        section_filter=section_filter,
        page_filter=page_filter,
    )


def source_reader_to_markdown(report: AnalysisReport, view: SourceReaderView | None = None) -> str:
    reader_view = view or build_source_reader_view(report)
    lines = [
        f"# Source Reader: {report.source_name}",
        "",
        f"- Verdict: **{report.verdict}**",
        f"- Confidence: **{report.confidence:.0%}**",
        f"- Selected anchor: **{reader_view.selected_anchor or 'none'}**",
    ]
    if reader_view.query:
        lines.append(f"- Search query: `{reader_view.query}`")
    if reader_view.section_filter:
        lines.append(f"- Section filter: {reader_view.section_filter}")
    if reader_view.page_filter is not None:
        lines.append(f"- Page filter: {reader_view.page_filter}")
    lines.append("")

    if not reader_view.selected_span:
        lines.extend(["No source anchors are available for this report.", ""])
        return "\n".join(lines)

    lines.extend(
        [
            "## Selected Source",
            "",
            f"- Source: {source_reference(reader_view.selected_span)}",
            "",
            f"> {reader_view.selected_span.text}",
            "",
            "## Nearby Context",
            "",
        ]
    )
    for span in reader_view.context_spans:
        marker = "selected" if span.anchor_id == reader_view.selected_anchor else "nearby"
        lines.extend(
            [
                f"### {span.anchor_id} - {marker}",
                "",
                f"- Source: {source_reference(span)}",
                "",
                f"> {span.text}",
                "",
            ]
        )

    lines.extend(["## Linked Audit Items", ""])
    if reader_view.related_items:
        for item in reader_view.related_items:
            lines.extend(
                [
                    f"### {item.id} - {item.title}",
                    "",
                    f"- Kind: {item.kind}",
                    f"- Status: {item.status}",
                    f"- Source: {source_reference(item.source_span)}",
                    f"- Related source: {source_reference(item.related_source_span)}",
                    f"- Summary: {item.body}",
                    f"- Rule explanation: {item.explanation}",
                    f"- Repair: {item.repair_suggestion}",
                    "",
                ]
            )
    else:
        lines.extend(["No audit items point directly to this anchor.", ""])

    if reader_view.query:
        lines.extend(["## Search Matches", ""])
        for anchor in reader_view.matching_anchors[:25]:
            lines.extend(
                [
                    f"- **{anchor.anchor_id}** - {anchor.reference} ({anchor.related_count} linked items)",
                    f"  - {truncate(anchor.text, 240)}",
                ]
            )
        if len(reader_view.matching_anchors) > 25:
            lines.append(f"- {len(reader_view.matching_anchors) - 25} more matches are available in the app.")
        lines.append("")

    lines.extend(
        [
            "_Source Reader exports contain selected source references, nearby snippets, linked issues, repair notes, and revision re-check summaries only. They do not include the full uploaded paper file._",
            "",
        ]
    )
    return "\n".join(lines)


def build_reader_related_items(
    report: AnalysisReport,
    repair_progress: Any = None,
    revision_rechecks: Any = None,
) -> list[SourceReaderRelatedItem]:
    items = [reader_item_from_review_item(item) for item in build_source_review_items(report)]
    normalized_rechecks = normalize_revision_rechecks(revision_rechecks or {})
    if normalized_rechecks:
        for step in build_repair_steps(report, repair_progress if isinstance(repair_progress, dict) else None):
            result = normalized_rechecks.get(step.id)
            if not result:
                continue
            status = str(result.get("status", "still-weak"))
            items.append(
                SourceReaderRelatedItem(
                    id=str(result.get("id", step.id)),
                    kind="Revision Re-Check",
                    title=revision_status_label(status),
                    status=status,
                    source_span=step.source_span,
                    related_source_span=None,
                    body=str(result.get("summary", "")),
                    explanation=f"Revision test for repair step {step.id}.",
                    repair_suggestion="Use the re-check result to decide whether this repair is ready, still weak, or introducing a new issue.",
                )
            )
    return sorted(deduplicate_related_items(items), key=related_item_sort_key)


def reader_item_from_review_item(item: SourceReviewItem) -> SourceReaderRelatedItem:
    return SourceReaderRelatedItem(
        id=item.id,
        kind=item.kind,
        title=item.title,
        status=item.status,
        source_span=item.source_span,
        related_source_span=item.related_source_span,
        body=item.body,
        explanation=item.explanation,
        repair_suggestion=item.repair_suggestion,
    )


def build_context_spans(source_spans: list[SourceSpan], selected_span: SourceSpan, radius: int = 2) -> list[SourceSpan]:
    selected_index = next(
        (index for index, span in enumerate(source_spans) if span.anchor_id == selected_span.anchor_id),
        0,
    )
    start = max(0, selected_index - max(1, radius))
    end = min(len(source_spans), selected_index + max(1, radius) + 1)
    return source_spans[start:end]


def source_span_matches(
    span: SourceSpan,
    query: str = "",
    section_filter: str | None = None,
    page_filter: int | None = None,
) -> bool:
    if section_filter and (span.section or "Document") != section_filter:
        return False
    if page_filter is not None and span.page_number != page_filter:
        return False
    if not query:
        return True
    haystack = " ".join([span.anchor_id, span.section or "", source_reference(span), span.text]).lower()
    return query.lower() in haystack


def clean_query(query: object) -> str:
    return " ".join(str(query or "").split())


def normalize_section_filter(section: object) -> str | None:
    if not isinstance(section, str):
        return None
    clean = section.strip()
    if not clean or clean.lower() == "all":
        return None
    return clean


def normalize_page_filter(page: object) -> int | None:
    if page is None:
        return None
    if isinstance(page, int):
        return page
    if isinstance(page, str):
        clean = page.strip().lower().replace("page", "").strip()
        if not clean or clean == "all":
            return None
        try:
            return int(clean)
        except ValueError:
            return None
    return None


def count_related_items_by_anchor(items: list[SourceReaderRelatedItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        for span in (item.source_span, item.related_source_span):
            if not span:
                continue
            counts[span.anchor_id] = counts.get(span.anchor_id, 0) + 1
    return counts


def deduplicate_related_items(items: list[SourceReaderRelatedItem]) -> list[SourceReaderRelatedItem]:
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[SourceReaderRelatedItem] = []
    for item in items:
        key = (
            item.kind,
            item.id,
            item.source_span.anchor_id if item.source_span else "",
            item.body,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def related_item_sort_key(item: SourceReaderRelatedItem) -> tuple[int, str, str]:
    kind_order = {
        "Finding": 0,
        "Claim": 1,
        "Evidence": 2,
        "Repair": 3,
        "Revision Re-Check": 4,
    }
    return (kind_order.get(item.kind, 9), item.status, item.id)


def same_anchor(span: SourceSpan | None, anchor_id: str) -> bool:
    return bool(span and span.anchor_id == anchor_id)


def truncate(text: str, limit: int) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."
