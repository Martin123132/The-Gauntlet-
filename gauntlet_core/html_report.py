from __future__ import annotations

from html import escape

from .models import AnalysisReport, SourceSpan, source_reference


def analysis_report_to_html(report: AnalysisReport) -> str:
    title = f"The Gauntlet Report: {report.source_name}"
    source_spans = prioritized_source_spans(report)
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{escape(title)}</title>",
            f"<style>{REPORT_CSS}</style>",
            "</head>",
            "<body>",
            '<main class="report-shell">',
            render_header(report),
            render_summary(report),
            render_claims(report),
            render_findings(report),
            render_evidence(report),
            render_source_highlights(source_spans),
            render_rubric(report),
            render_issue_brief(report),
            render_footer(),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def render_header(report: AnalysisReport) -> str:
    return f"""
<section class="hero">
  <div>
    <p class="eyebrow">The Gauntlet Local Report</p>
    <h1>{escape(report.source_name)}</h1>
    <p>{escape(report.summary)}</p>
  </div>
  <div class="verdict {escape(report.verdict.lower())}">
    <span>Verdict</span>
    <strong>{escape(report.verdict)}</strong>
    <small>Confidence {report.confidence:.0%}</small>
  </div>
</section>
"""


def render_summary(report: AnalysisReport) -> str:
    metrics = [
        ("Claims", str(len(report.claims)), f"{report.resolved_claims} resolved"),
        ("Findings", str(len(report.findings)), f"{report.high_severity_findings} high severity"),
        ("Evidence", f"{report.evidence.score:.2f}", "0 to 1 score"),
        ("Sentences", str(report.sentence_count), f"{report.word_count} words"),
    ]
    metric_html = "".join(render_metric(label, value, note) for label, value, note in metrics)
    sections = ", ".join(report.sections) if report.sections else "Document"
    return f"""
<section class="panel">
  <h2>Summary</h2>
  <div class="metric-grid">{metric_html}</div>
  <div class="meta-grid">
    <div><span>Generated</span><strong>{escape(report.created_at)}</strong></div>
    <div><span>Sections</span><strong>{escape(sections)}</strong></div>
    <div><span>Source Anchors</span><strong>{len(report.source_spans)}</strong></div>
  </div>
</section>
"""


def render_claims(report: AnalysisReport) -> str:
    if not report.claims:
        content = '<p class="empty">No clear resolution claims were detected.</p>'
    else:
        content = "".join(render_claim_card(claim) for claim in report.claims)
    return f"""
<section class="panel">
  <h2>Claims</h2>
  <div class="card-grid">{content}</div>
</section>
"""


def render_claim_card(claim) -> str:
    gaps = ", ".join(claim.gaps) if claim.gaps else "none"
    links = ", ".join(link.id for link in claim.evidence_links) if claim.evidence_links else "none"
    rubric = "".join(
        f"<li>{escape(score.name)}: {score.score:.2f} - {escape(score.reason)}</li>" for score in claim.rubric_scores
    )
    source = source_reference(claim.source_span)
    source_text = render_source_quote(claim.source_span)
    return f"""
<article class="card">
  <div class="card-head">
    <strong>{escape(claim.id or "Claim")}</strong>
    <span class="pill {escape(claim.status)}">{escape(claim.status.title())}</span>
  </div>
  <p>{escape(claim.claim)}</p>
  <p class="source-ref">{escape(source)}</p>
  {source_text}
  <dl>
    <dt>Quality</dt><dd>{claim.quality:.2f}</dd>
    <dt>Evidence</dt><dd>{claim.evidence_strength:.2f}</dd>
    <dt>Mechanism</dt><dd>{escape(claim.mechanism)}</dd>
    <dt>Gaps</dt><dd>{escape(gaps)}</dd>
    <dt>Links</dt><dd>{escape(links)}</dd>
  </dl>
  <p class="repair"><strong>Repair:</strong> {escape(claim.repair_suggestion or "No immediate repair suggested.")}</p>
  <ul>{rubric}</ul>
</article>
"""


def render_findings(report: AnalysisReport) -> str:
    if not report.findings:
        content = '<p class="empty">No internal contradictions were detected by the rule set.</p>'
    else:
        content = "".join(render_finding_card(finding) for finding in report.findings)
    return f"""
<section class="panel">
  <h2>Findings</h2>
  <div class="card-grid">{content}</div>
</section>
"""


def render_finding_card(finding) -> str:
    related = ""
    if finding.related_sentence:
        related = f'<p><strong>Related:</strong> {escape(finding.related_sentence)}</p>'
    related_source = ""
    if finding.related_source_span:
        related_source = f'<p class="source-ref">Related: {escape(source_reference(finding.related_source_span))}</p>'
    return f"""
<article class="card finding {escape(finding.severity)}">
  <div class="card-head">
    <strong>{escape(finding.id or finding.type)} - {escape(finding.type)}</strong>
    <span class="pill {escape(finding.severity)}">{escape(finding.severity.title())}</span>
  </div>
  <p>{escape(finding.sentence)}</p>
  <p class="source-ref">{escape(source_reference(finding.source_span))}</p>
  {render_source_quote(finding.source_span)}
  {related}
  {related_source}
  <p><strong>Why it matters:</strong> {escape(finding.explanation)}</p>
  <p class="repair"><strong>Repair:</strong> {escape(finding.repair_suggestion)}</p>
</article>
"""


def render_evidence(report: AnalysisReport) -> str:
    profile = report.evidence
    metrics = [
        ("Quantitative", str(profile.quantitative_evidence), "numbers and measurements"),
        ("Math", str(profile.mathematical_content), "equations and formal notation"),
        ("Citations", str(profile.citations), "citation-like references"),
        ("Methods", str(profile.methodology_terms), "methodology terms"),
    ]
    links = "".join(render_evidence_link(link) for link in profile.evidence_links)
    if not links:
        links = '<p class="empty">No evidence snippets were indexed.</p>'
    return f"""
<section class="panel">
  <h2>Evidence Profile</h2>
  <div class="metric-grid">{''.join(render_metric(label, value, note) for label, value, note in metrics)}</div>
  <div class="bar"><span style="width:{pct(profile.score)}%"></span></div>
  <p class="muted">Evidence quality: {profile.score:.2f}/1.00. Linked snippets: {profile.linked_evidence}.</p>
  <div class="card-grid">{links}</div>
</section>
"""


def render_evidence_link(link) -> str:
    return f"""
<article class="card compact">
  <div class="card-head">
    <strong>{escape(link.id)} - {escape(link.type.title())}</strong>
    <span class="pill resolved">{link.confidence:.0%}</span>
  </div>
  <p>{escape(link.snippet)}</p>
  <p class="source-ref">{escape(source_reference(link.source_span))}</p>
  {render_source_quote(link.source_span)}
</article>
"""


def render_source_highlights(source_spans: list[SourceSpan]) -> str:
    if not source_spans:
        content = '<p class="empty">No source trace was recorded.</p>'
    else:
        visible_spans = source_spans[:40]
        content = "".join(render_source_card(span) for span in visible_spans)
        if len(source_spans) > len(visible_spans):
            content += f'<p class="muted">Showing 40 of {len(source_spans)} source anchors.</p>'
    return f"""
<section class="panel">
  <h2>Source Highlights</h2>
  <p class="muted">Exact extracted sentences used by the local audit. Page numbers appear when the loader can recover them.</p>
  <div class="source-list">{content}</div>
</section>
"""


def render_source_card(span: SourceSpan) -> str:
    return f"""
<article class="source-card">
  <strong>{escape(span.anchor_id)}</strong>
  <span>{escape(source_reference(span))}</span>
  <p>{escape(span.text)}</p>
</article>
"""


def render_rubric(report: AnalysisReport) -> str:
    if not report.verdict_rubric:
        content = '<p class="empty">No rubric details were recorded.</p>'
    else:
        content = "".join(
            f"""
<article class="rubric-row">
  <strong>{escape(score.name)}</strong>
  <div class="bar"><span style="width:{pct(score.score)}%"></span></div>
  <em>{score.score:.2f} x {score.weight:.2f}</em>
  <p>{escape(score.reason)}</p>
</article>
"""
            for score in report.verdict_rubric
        )
    return f"""
<section class="panel">
  <h2>Verdict Rubric</h2>
  {content}
</section>
"""


def render_issue_brief(report: AnalysisReport) -> str:
    brief = report.issue_brief or "No issue brief was generated."
    return f"""
<section class="panel">
  <h2>Issue Brief</h2>
  <pre>{escape(brief)}</pre>
</section>
"""


def render_footer() -> str:
    return """
<footer>
  <strong>Privacy note:</strong> This HTML report was produced from deterministic local rules. No AI model or API provider was used unless the user separately ran optional refinement. API keys and uploaded paper files are not embedded in this report.
</footer>
"""


def render_metric(label: str, value: str, note: str) -> str:
    return f"""
<div class="metric">
  <span>{escape(label)}</span>
  <strong>{escape(value)}</strong>
  <small>{escape(note)}</small>
</div>
"""


def render_source_quote(span: SourceSpan | None) -> str:
    if not span:
        return ""
    return f'<blockquote><strong>Source text:</strong> {escape(span.text)}</blockquote>'


def prioritized_source_spans(report: AnalysisReport) -> list[SourceSpan]:
    by_anchor = {span.anchor_id: span for span in report.source_spans}
    priority: list[str] = []
    for claim in report.claims:
        add_anchor(priority, claim.source_span)
        for link in claim.evidence_links:
            add_anchor(priority, link.source_span)
    for finding in report.findings:
        add_anchor(priority, finding.source_span)
        add_anchor(priority, finding.related_source_span)
    for link in report.evidence.evidence_links:
        add_anchor(priority, link.source_span)
    ordered = [by_anchor[anchor] for anchor in priority if anchor in by_anchor]
    ordered_ids = set(priority)
    ordered.extend(span for span in report.source_spans if span.anchor_id not in ordered_ids)
    return ordered


def add_anchor(anchor_ids: list[str], span: SourceSpan | None) -> None:
    if span and span.anchor_id and span.anchor_id not in anchor_ids:
        anchor_ids.append(span.anchor_id)


def pct(value: float) -> int:
    return int(max(0, min(100, value * 100)))


REPORT_CSS = """
:root {
  color-scheme: light;
  --ink: #14191f;
  --muted: #607080;
  --border: #dce4ea;
  --soft: #f5f8fa;
  --teal: #07877f;
  --amber: #d48806;
  --red: #d92d20;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: #f7f9fb;
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.5;
}
.report-shell {
  width: min(1180px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 28px 0 40px;
}
.hero, .panel, footer {
  background: white;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 14px 38px rgba(18, 34, 51, .07);
  margin-bottom: 18px;
  padding: 22px;
}
.hero {
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: 24px;
  align-items: center;
}
.eyebrow, .metric span, .source-card span, dt {
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}
h1, h2, p { margin-top: 0; }
h1 { font-size: 34px; line-height: 1.1; margin-bottom: 12px; }
h2 { font-size: 22px; margin-bottom: 16px; }
.verdict {
  border-radius: 8px;
  border: 1px solid #c7e2df;
  background: #effaf8;
  padding: 20px;
  text-align: center;
}
.verdict span, .verdict small { display: block; color: var(--muted); font-weight: 800; }
.verdict strong { display: block; color: var(--teal); font-size: 28px; margin: 8px 0; }
.verdict.partial strong { color: var(--amber); }
.verdict.fails strong, .verdict.creates_new_paradoxes strong { color: var(--red); }
.metric-grid, .card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.metric, .card, .source-card, .rubric-row {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fff;
  padding: 14px;
}
.metric strong { display: block; font-size: 26px; margin: 4px 0; }
.metric small, .muted { color: var(--muted); }
.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}
.meta-grid div { background: var(--soft); border-radius: 8px; padding: 12px; }
.meta-grid span { display: block; color: var(--muted); font-size: 12px; font-weight: 800; }
.card-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
}
.pill {
  border-radius: 999px;
  padding: 3px 9px;
  font-size: 12px;
  font-weight: 850;
  background: #e6f6f3;
  color: var(--teal);
}
.pill.partial, .pill.medium { background: #fff5df; color: var(--amber); }
.pill.failed, .pill.high { background: #ffe8e6; color: var(--red); }
.source-ref {
  display: inline-block;
  color: var(--teal);
  background: #effaf8;
  border: 1px solid #c7e2df;
  border-radius: 6px;
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 800;
}
blockquote {
  margin: 12px 0;
  border-left: 3px solid var(--teal);
  background: #fbfcfd;
  padding: 10px 12px;
}
dl {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 6px 12px;
}
dd { margin: 0; }
.repair { color: #273340; }
.bar {
  height: 10px;
  border-radius: 999px;
  background: #e9eef2;
  overflow: hidden;
  margin: 10px 0;
}
.bar span {
  display: block;
  height: 100%;
  background: var(--teal);
}
.source-list { display: grid; gap: 10px; }
.source-card {
  border-left: 3px solid var(--teal);
}
.source-card strong { display: block; margin-bottom: 2px; }
.source-card p { margin: 8px 0 0; }
.rubric-row { margin-bottom: 10px; }
.rubric-row em { color: var(--muted); font-style: normal; font-weight: 800; }
.empty { color: var(--muted); background: var(--soft); border-radius: 8px; padding: 14px; }
pre {
  white-space: pre-wrap;
  margin: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fbfcfd;
  padding: 14px;
  font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
}
footer { color: var(--muted); }
@media (max-width: 820px) {
  .hero, .metric-grid, .meta-grid, .card-grid { grid-template-columns: 1fr; }
  .report-shell { width: min(100vw - 20px, 1180px); padding-top: 12px; }
}
"""
