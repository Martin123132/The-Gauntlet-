from __future__ import annotations

from io import BytesIO
import html as html_lib
import json
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from .evidence_map import build_claim_evidence_map, claim_evidence_map_to_markdown
from .models import AnalysisReport, SourceSpan, source_reference
from .repair_workshop import build_repair_steps, repair_status_label, repair_workshop_to_markdown
from .report_bundle import safe_report_stem
from .revision_recheck import (
    normalize_revision_rechecks,
    revision_recheck_log_to_markdown,
    revision_status_label,
)
from .source_review import SourceReviewItem, build_source_review_items, source_review_to_markdown
from .workspace import normalize_issue_reviews, normalize_repair_progress


PRIVACY_NOTE = (
    "Reviewer Packet exports contain verdicts, issue summaries, reviewer notes, "
    "repair progress, revision snippets, source references, and linked source "
    "snippets only. They do not include the full uploaded paper file or API keys."
)


def reviewer_packet_to_markdown(
    report: AnalysisReport,
    issue_reviews: dict[str, Any] | None = None,
    repair_progress: dict[str, Any] | None = None,
    revision_rechecks: dict[str, Any] | None = None,
) -> str:
    """Build a reviewer-facing packet from report data plus saved workspace state."""
    reviews = normalize_issue_reviews(issue_reviews or {})
    progress = normalize_repair_progress(repair_progress or {})
    rechecks = normalize_revision_rechecks(revision_rechecks or {})
    review_items = build_source_review_items(report)
    repair_steps = build_repair_steps(report, progress)

    lines = [
        f"# Reviewer Packet: {report.source_name}",
        "",
        "## Executive Summary",
        "",
        f"- Verdict: **{report.verdict}**",
        f"- Confidence: **{report.confidence:.0%}**",
        f"- Evidence quality: **{report.evidence.score:.2f}/1.00**",
        f"- Claims: **{len(report.claims)}**",
        f"- Findings: **{len(report.findings)}**",
        f"- Issue reviews: **{len(reviews)} saved**",
        f"- Repair steps: **{len(repair_steps)}**",
        f"- Revision re-checks: **{len(rechecks)} saved**",
        "",
        report.summary,
        "",
        "## Issue Review Register",
        "",
    ]
    lines.extend(issue_review_register_markdown(review_items, reviews))
    lines.extend(
        [
            "## Claim-Evidence Map",
            "",
            claim_evidence_map_to_markdown(report, build_claim_evidence_map(report)),
            "## Repair Workshop Checklist",
            "",
            repair_workshop_to_markdown(report, repair_steps),
            "## Source Review Extract",
            "",
            source_review_to_markdown(report, review_items),
            "## Revision Re-Check Log",
            "",
            revision_recheck_log_to_markdown(report, rechecks),
            "## Privacy Note",
            "",
            PRIVACY_NOTE,
            "",
        ]
    )
    return "\n".join(lines)


def reviewer_packet_to_html(
    report: AnalysisReport,
    issue_reviews: dict[str, Any] | None = None,
    repair_progress: dict[str, Any] | None = None,
    revision_rechecks: dict[str, Any] | None = None,
) -> str:
    """Build a self-contained HTML reviewer packet."""
    reviews = normalize_issue_reviews(issue_reviews or {})
    progress = normalize_repair_progress(repair_progress or {})
    rechecks = normalize_revision_rechecks(revision_rechecks or {})
    review_items = build_source_review_items(report)
    repair_steps = build_repair_steps(report, progress)
    claim_map = build_claim_evidence_map(report)

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{escape(report.source_name)} Reviewer Packet</title>",
            "<style>",
            html_styles(),
            "</style>",
            "</head>",
            "<body>",
            "<main>",
            "<section class=\"hero\">",
            "<div>",
            "<p class=\"eyebrow\">The Gauntlet Reviewer Packet</p>",
            f"<h1>{escape(report.source_name)}</h1>",
            f"<p>{escape(report.summary)}</p>",
            "</div>",
            "<div class=\"verdict-card\">",
            f"<span>Verdict</span><strong>{escape(report.verdict)}</strong>",
            f"<span>Confidence</span><strong>{report.confidence:.0%}</strong>",
            f"<span>Evidence</span><strong>{report.evidence.score:.2f}/1.00</strong>",
            "</div>",
            "</section>",
            metric_grid_html(
                {
                    "Claims": len(report.claims),
                    "Findings": len(report.findings),
                    "Issue reviews": len(reviews),
                    "Repair steps": len(repair_steps),
                    "Revision checks": len(rechecks),
                }
            ),
            section_html("Issue Review Register", issue_review_register_html(review_items, reviews)),
            section_html("Claim-Evidence Map", claim_evidence_map_html(claim_map)),
            section_html("Repair Workshop Checklist", repair_steps_html(repair_steps)),
            section_html("Revision Re-Check Log", revision_rechecks_html(rechecks)),
            section_html("Privacy Note", f"<p>{escape(PRIVACY_NOTE)}</p>"),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def build_reviewer_packet_bundle(
    report: AnalysisReport,
    issue_reviews: dict[str, Any] | None = None,
    repair_progress: dict[str, Any] | None = None,
    revision_rechecks: dict[str, Any] | None = None,
) -> bytes:
    """Build a ZIP with Markdown, HTML, and review-state metadata."""
    stem = safe_report_stem(report.source_name)
    markdown_name = f"{stem}-reviewer-packet.md"
    html_name = f"{stem}-reviewer-packet.html"
    review_state_name = f"{stem}-review-state.json"
    readme_name = "README.txt"

    reviews = normalize_issue_reviews(issue_reviews or {})
    progress = normalize_repair_progress(repair_progress or {})
    rechecks = normalize_revision_rechecks(revision_rechecks or {})
    review_state = {
        "source_name": report.source_name,
        "verdict": report.verdict,
        "confidence": report.confidence,
        "issue_reviews": reviews,
        "repair_progress": progress,
        "revision_recheck_summary": {
            step_id: {
                "id": item.get("id", ""),
                "step_id": item.get("step_id", step_id),
                "status": item.get("status", ""),
                "checked_at": item.get("checked_at", ""),
                "summary": item.get("summary", ""),
            }
            for step_id, item in rechecks.items()
        },
    }

    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr(markdown_name, reviewer_packet_to_markdown(report, reviews, progress, rechecks))
        bundle.writestr(html_name, reviewer_packet_to_html(report, reviews, progress, rechecks))
        bundle.writestr(review_state_name, json.dumps(review_state, indent=2))
        bundle.writestr(readme_name, reviewer_packet_readme(report, [markdown_name, html_name, review_state_name]))
    return buffer.getvalue()


def reviewer_packet_readme(report: AnalysisReport, files: list[str]) -> str:
    file_lines = "\n".join(f"- {name}" for name in files)
    return "\n".join(
        [
            "The Gauntlet Reviewer Packet",
            "",
            f"Source: {report.source_name}",
            f"Verdict: {report.verdict}",
            f"Confidence: {report.confidence:.0%}",
            f"Generated: {report.created_at}",
            "",
            "Included files:",
            file_lines,
            "",
            "Markdown is best for review comments or GitHub issues. HTML is best for a readable offline packet. JSON contains saved review state summaries for automation.",
            "",
            f"Privacy note: {PRIVACY_NOTE}",
            "",
        ]
    )


def issue_review_register_markdown(items: list[SourceReviewItem], reviews: dict[str, dict[str, str]]) -> list[str]:
    if not items and not reviews:
        return ["No issue review items were generated.", ""]
    lines: list[str] = []
    seen_ids: set[str] = set()
    for item in items:
        seen_ids.add(item.id)
        review = reviews.get(item.id, {})
        lines.extend(
            [
                f"### {item.id} - {item.title}",
                "",
                f"- Kind: {item.kind}",
                f"- Severity: {item.severity}",
                f"- Review status: {issue_review_label(review.get('status', 'unreviewed'))}",
                f"- Source: {source_reference(item.source_span)}",
                f"- Issue: {item.body}",
                f"- Rule explanation: {item.explanation}",
                f"- Repair suggestion: {item.repair_suggestion}",
            ]
        )
        reviewer_note = review.get("reviewer_note", "").strip()
        if reviewer_note:
            lines.append(f"- Reviewer note: {reviewer_note}")
        updated_at = review.get("updated_at", "").strip()
        if updated_at:
            lines.append(f"- Updated: {updated_at}")
        lines.append("")
        if item.source_span:
            lines.extend([f"> Source text: {item.source_span.text}", ""])
        if item.related_source_span:
            lines.extend([f"> Related source text: {item.related_source_span.text}", ""])
    for issue_id, review in sorted(reviews.items()):
        if issue_id in seen_ids:
            continue
        lines.extend(
            [
                f"### {issue_id} - Saved issue review",
                "",
                f"- Review status: {issue_review_label(review.get('status', 'unreviewed'))}",
                f"- Reviewer note: {review.get('reviewer_note', '').strip() or 'none'}",
                f"- Updated: {review.get('updated_at', '').strip() or 'unknown'}",
                "",
            ]
        )
    return lines


def issue_review_register_html(items: list[SourceReviewItem], reviews: dict[str, dict[str, str]]) -> str:
    if not items and not reviews:
        return '<p class="empty">No issue review items were generated.</p>'
    cards: list[str] = []
    seen_ids: set[str] = set()
    for item in items:
        seen_ids.add(item.id)
        review = reviews.get(item.id, {})
        cards.append(
            card_html(
                title=f"{item.id} - {item.title}",
                meta=[
                    item.kind,
                    item.severity.title(),
                    issue_review_label(review.get("status", "unreviewed")),
                    source_reference(item.source_span),
                ],
                body=[
                    ("Issue", item.body),
                    ("Rule explanation", item.explanation),
                    ("Repair suggestion", item.repair_suggestion),
                    ("Reviewer note", review.get("reviewer_note", "").strip()),
                    ("Updated", review.get("updated_at", "").strip()),
                    ("Source text", source_text(item.source_span)),
                    ("Related source text", source_text(item.related_source_span)),
                ],
            )
        )
    for issue_id, review in sorted(reviews.items()):
        if issue_id in seen_ids:
            continue
        cards.append(
            card_html(
                title=f"{issue_id} - Saved issue review",
                meta=[issue_review_label(review.get("status", "unreviewed"))],
                body=[
                    ("Reviewer note", review.get("reviewer_note", "")),
                    ("Updated", review.get("updated_at", "")),
                ],
            )
        )
    return "\n".join(cards)


def claim_evidence_map_html(claim_map) -> str:
    if not claim_map.rows:
        return '<p class="empty">No clear claims were detected, so no claim-evidence rows were generated.</p>'
    rows: list[str] = []
    for row in claim_map.rows:
        evidence = "\n".join(
            f"{link.id} ({link.type}, {link.confidence:.0%}) - {source_reference(link.source_span)}: {link.snippet}"
            for link in row.evidence_links
        )
        rows.append(
            card_html(
                title=f"{row.claim_id} - {row.coverage.title()}",
                meta=[row.claim_status, row.priority, source_reference(row.source_span)],
                body=[
                    ("Claim", row.claim),
                    ("Evidence strength", f"{row.evidence_strength:.2f}"),
                    ("Evidence links", evidence or "No linked evidence snippets."),
                    ("Gaps", ", ".join(row.gaps) if row.gaps else "none"),
                    ("Repair", row.repair_suggestion),
                    ("Claim source", source_text(row.source_span)),
                ],
            )
        )
    if claim_map.orphan_evidence_links:
        orphan_lines = "\n".join(
            f"{link.id} ({link.type}, {link.confidence:.0%}) - {source_reference(link.source_span)}: {link.snippet}"
            for link in claim_map.orphan_evidence_links
        )
        rows.append(card_html("Orphan Evidence", [f"{len(claim_map.orphan_evidence_links)} snippets"], [("Evidence", orphan_lines)]))
    return "\n".join(rows)


def repair_steps_html(steps) -> str:
    if not steps:
        return '<p class="empty">No repair steps were generated.</p>'
    cards = []
    for step in steps:
        cards.append(
            card_html(
                title=f"{step.id} - {step.title}",
                meta=[
                    step.priority.upper(),
                    repair_status_label(step.status),
                    step.category,
                    source_reference(step.source_span),
                ],
                body=[
                    ("Target", step.target),
                    ("Issue", step.body),
                    ("Rule explanation", step.explanation),
                    ("Suggested fix", step.suggested_fix),
                    ("Reviewer note", step.reviewer_note),
                    ("Updated", step.updated_at),
                    ("Source text", source_text(step.source_span)),
                ],
            )
        )
    return "\n".join(cards)


def revision_rechecks_html(rechecks: dict[str, dict[str, Any]]) -> str:
    if not rechecks:
        return '<p class="empty">No revision re-checks have been saved.</p>'
    cards = []
    for result in sorted(rechecks.values(), key=lambda item: item.get("checked_at", ""), reverse=True):
        cards.append(
            card_html(
                title=f"{result.get('id', 'Revision')} - {revision_status_label(result.get('status', 'still-weak'))}",
                meta=[str(result.get("step_id", "")), str(result.get("checked_at", ""))],
                body=[
                    ("Original verdict", str(result.get("original_verdict", ""))),
                    ("Revised verdict", str(result.get("revised_verdict", ""))),
                    ("Gap count", f"{result.get('original_gap_count', 0)} -> {result.get('revised_gap_count', 0)}"),
                    ("Finding count", f"{result.get('original_finding_count', 0)} -> {result.get('revised_finding_count', 0)}"),
                    ("Remaining gaps", ", ".join(result.get("remaining_gaps", ())) or "none"),
                    ("New findings", ", ".join(result.get("new_findings", ())) or "none"),
                    ("Summary", str(result.get("summary", ""))),
                    ("Original snippet", str(result.get("original_text", ""))),
                    ("Revised snippet", str(result.get("revised_text", ""))),
                ],
            )
        )
    return "\n".join(cards)


def metric_grid_html(metrics: dict[str, int]) -> str:
    cards = "\n".join(
        f'<div class="metric"><span>{escape(label)}</span><strong>{value}</strong></div>'
        for label, value in metrics.items()
    )
    return f'<section class="metrics">{cards}</section>'


def section_html(title: str, content: str) -> str:
    return f'<section class="packet-section"><h2>{escape(title)}</h2>{content}</section>'


def card_html(title: str, meta: list[str], body: list[tuple[str, str]]) -> str:
    meta_html = "".join(f"<span>{escape(value)}</span>" for value in meta if value)
    body_html = ""
    for label, value in body:
        if value is None:
            continue
        clean = str(value).strip()
        if not clean:
            continue
        escaped_value = escape(clean).replace("\n", "<br>")
        body_html += f"<h3>{escape(label)}</h3><p>{escaped_value}</p>"
    return f'<article class="packet-card"><div class="card-meta">{meta_html}</div><h3>{escape(title)}</h3>{body_html}</article>'


def source_text(span: SourceSpan | None) -> str:
    return span.text if span else ""


def issue_review_label(status: str | None) -> str:
    labels = {
        "unreviewed": "Unreviewed",
        "confirmed": "Confirmed",
        "false-positive": "False Positive",
        "needs-repair": "Needs Repair",
        "resolved": "Resolved",
    }
    return labels.get(status or "unreviewed", str(status or "unreviewed").replace("-", " ").title())


def escape(value: object) -> str:
    return html_lib.escape(str(value), quote=True)


def html_styles() -> str:
    return """
:root {
  color-scheme: light;
  --ink: #172022;
  --muted: #61706f;
  --line: #d8e2df;
  --paper: #f7faf8;
  --card: #ffffff;
  --accent: #0f766e;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 15px/1.55 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
main {
  width: min(1120px, calc(100% - 40px));
  margin: 0 auto;
  padding: 40px 0 64px;
}
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 24px;
  align-items: stretch;
  border-bottom: 1px solid var(--line);
  padding-bottom: 28px;
}
.eyebrow {
  margin: 0 0 10px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
}
h1 {
  margin: 0 0 12px;
  font-size: clamp(34px, 5vw, 56px);
  line-height: 1;
}
h2 {
  margin: 34px 0 16px;
  font-size: 24px;
}
.verdict-card,
.metric,
.packet-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 18px 38px rgba(23, 32, 34, .06);
}
.verdict-card {
  display: grid;
  gap: 10px;
  padding: 20px;
}
.verdict-card span,
.metric span,
.card-meta span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.verdict-card strong {
  font-size: 26px;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-top: 22px;
}
.metric {
  padding: 16px;
}
.metric strong {
  display: block;
  margin-top: 6px;
  font-size: 28px;
}
.packet-section {
  margin-top: 18px;
}
.packet-card {
  padding: 18px;
  margin-bottom: 14px;
  overflow-wrap: anywhere;
}
.packet-card h3 {
  margin: 9px 0 8px;
  font-size: 17px;
}
.packet-card h3 + h3 {
  margin-top: 18px;
}
.packet-card p {
  margin: 0 0 10px;
}
.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.card-meta span {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 3px 8px;
  background: #f9fbfa;
}
.empty {
  color: var(--muted);
  border: 1px dashed var(--line);
  border-radius: 8px;
  padding: 18px;
  background: rgba(255, 255, 255, .6);
}
@media (max-width: 760px) {
  main { width: min(100% - 24px, 1120px); }
  .hero { grid-template-columns: 1fr; }
}
"""
