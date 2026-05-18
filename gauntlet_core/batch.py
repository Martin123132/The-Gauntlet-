from __future__ import annotations

import csv
from html import escape
import json
from dataclasses import dataclass, field
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from .action_plan import action_plan_to_markdown
from .models import AnalysisReport
from .report_bundle import safe_report_stem


BatchSortKey = str


@dataclass(frozen=True)
class BatchScanItem:
    source_name: str
    status: str
    verdict: str = ""
    confidence: float = 0.0
    evidence_score: float = 0.0
    claim_count: int = 0
    finding_count: int = 0
    high_severity_findings: int = 0
    top_findings: list[str] = field(default_factory=list)
    error: str = ""
    report: AnalysisReport | None = field(default=None, repr=False, compare=False)

    def to_summary_dict(self) -> dict[str, object]:
        return {
            "source_name": self.source_name,
            "status": self.status,
            "verdict": self.verdict,
            "confidence": round(self.confidence, 4),
            "evidence_score": round(self.evidence_score, 4),
            "claim_count": self.claim_count,
            "finding_count": self.finding_count,
            "high_severity_findings": self.high_severity_findings,
            "top_findings": "; ".join(self.top_findings),
            "error": self.error,
        }


def summarize_report(report: AnalysisReport) -> BatchScanItem:
    top_findings = []
    for finding in report.findings:
        label = finding.type
        if label not in top_findings:
            top_findings.append(label)
        if len(top_findings) >= 3:
            break
    return BatchScanItem(
        source_name=report.source_name,
        status="analyzed",
        verdict=report.verdict,
        confidence=report.confidence,
        evidence_score=report.evidence.score,
        claim_count=len(report.claims),
        finding_count=len(report.findings),
        high_severity_findings=report.high_severity_findings,
        top_findings=top_findings,
        report=report,
    )


def build_demo_batch_items() -> list[BatchScanItem]:
    from .benchmarks import run_all_benchmarks

    return [summarize_report(comparison.report) for comparison in run_all_benchmarks()]


def failed_batch_item(source_name: str, error: str) -> BatchScanItem:
    return BatchScanItem(source_name=source_name, status="failed", error=error)


def filter_batch_items(
    items: list[BatchScanItem],
    verdicts: set[str] | None = None,
    high_risk_only: bool = False,
    weak_evidence_only: bool = False,
) -> list[BatchScanItem]:
    filtered: list[BatchScanItem] = []
    for item in items:
        verdict_value = item.verdict if item.status == "analyzed" else "PARSE_FAILED"
        if verdicts and verdict_value not in verdicts:
            continue
        if high_risk_only and not is_high_risk_item(item):
            continue
        if weak_evidence_only and not is_weak_evidence_item(item):
            continue
        filtered.append(item)
    return filtered


def sort_batch_items(items: list[BatchScanItem], sort_by: BatchSortKey) -> list[BatchScanItem]:
    if sort_by == "Highest risk":
        return sorted(items, key=batch_risk_sort_key)
    if sort_by == "Most findings":
        return sorted(items, key=lambda item: (-item.finding_count, -item.high_severity_findings, item.source_name.lower()))
    if sort_by == "Lowest evidence":
        return sorted(items, key=lambda item: (item.evidence_score if item.status == "analyzed" else 2, item.source_name.lower()))
    if sort_by == "Highest confidence":
        return sorted(items, key=lambda item: (-item.confidence, item.source_name.lower()))
    if sort_by == "Lowest confidence":
        return sorted(items, key=lambda item: (item.confidence if item.status == "analyzed" else 2, item.source_name.lower()))
    if sort_by == "Filename":
        return sorted(items, key=lambda item: item.source_name.lower())
    if sort_by == "Verdict":
        verdict_order = {"CREATES_NEW_PARADOXES": 0, "FAILS": 1, "PARTIAL": 2, "RESOLVES": 3, "": 4}
        return sorted(items, key=lambda item: (verdict_order.get(item.verdict, 5), item.source_name.lower()))
    return list(items)


def is_high_risk_item(item: BatchScanItem) -> bool:
    return item.status == "failed" or item.high_severity_findings > 0 or item.verdict in {"CREATES_NEW_PARADOXES", "FAILS"}


def is_weak_evidence_item(item: BatchScanItem, threshold: float = 0.35) -> bool:
    return item.status == "analyzed" and item.evidence_score < threshold


def batch_risk_sort_key(item: BatchScanItem) -> tuple[int, float, int, str]:
    verdict_order = {"CREATES_NEW_PARADOXES": 0, "FAILS": 1, "PARTIAL": 2, "RESOLVES": 3}
    if item.status == "failed":
        return (0, 0.0, 0, item.source_name.lower())
    return (
        verdict_order.get(item.verdict, 4),
        item.evidence_score,
        -item.finding_count,
        item.source_name.lower(),
    )


def batch_items_to_csv(items: list[BatchScanItem]) -> str:
    output = StringIO()
    fieldnames = list(BatchScanItem("paper", "pending").to_summary_dict().keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for item in items:
        writer.writerow(item.to_summary_dict())
    return output.getvalue()


def batch_items_to_json(items: list[BatchScanItem]) -> str:
    return json.dumps([item.to_summary_dict() for item in items], indent=2)


def batch_items_to_markdown(items: list[BatchScanItem]) -> str:
    lines = [
        "# The Gauntlet Batch Scan",
        "",
        f"- Papers scanned: **{len(items)}**",
        f"- Analyzed: **{sum(1 for item in items if item.status == 'analyzed')}**",
        f"- Failed: **{sum(1 for item in items if item.status == 'failed')}**",
        "",
        "| Paper | Status | Verdict | Confidence | Evidence | Claims | Findings | Top Findings |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in items:
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_markdown_cell(item.source_name),
                    item.status,
                    item.verdict or "-",
                    f"{item.confidence:.0%}" if item.status == "analyzed" else "-",
                    f"{item.evidence_score:.2f}" if item.status == "analyzed" else "-",
                    str(item.claim_count) if item.status == "analyzed" else "-",
                    str(item.finding_count) if item.status == "analyzed" else "-",
                    escape_markdown_cell("; ".join(item.top_findings) or item.error or "-"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "_Batch scans are deterministic and local. The summary contains verdict metadata and source snippets only through the included per-paper reports._",
            "",
        ]
    )
    return "\n".join(lines)


def batch_items_to_html(items: list[BatchScanItem], report_stems: list[str | None] | None = None) -> str:
    if report_stems is None:
        report_stems = batch_report_stems(items)
    analyzed = sum(1 for item in items if item.status == "analyzed")
    failed = sum(1 for item in items if item.status == "failed")
    high_risk = sum(1 for item in items if is_high_risk_item(item))
    avg_evidence = sum(item.evidence_score for item in items if item.status == "analyzed") / analyzed if analyzed else 0
    rows = "\n".join(render_batch_html_row(item, report_stem) for item, report_stem in zip(items, report_stems))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>The Gauntlet Batch Scan</title>",
            f"<style>{BATCH_INDEX_CSS}</style>",
            "</head>",
            "<body>",
            '<main class="batch-shell">',
            '<section class="hero">',
            "<div>",
            '<p class="eyebrow">The Gauntlet Batch Bundle</p>',
            "<h1>Batch Scan Index</h1>",
            "<p>Offline summary for this deterministic local paper scan. Open a paper report to inspect claims, findings, source snippets, evidence links, and the reviewer action plan.</p>",
            "</div>",
            '<div class="privacy-card">',
            "<span>Privacy</span>",
            "<strong>Reports + snippets only</strong>",
            "<small>No uploaded paper files or API keys are included.</small>",
            "</div>",
            "</section>",
            '<section class="metric-grid">',
            render_batch_metric("Papers", str(len(items)), "included in this bundle"),
            render_batch_metric("Analyzed", str(analyzed), "completed reports"),
            render_batch_metric("High Risk", str(high_risk), "failed or severe results"),
            render_batch_metric("Avg Evidence", f"{avg_evidence:.2f}", "analyzed papers only"),
            render_batch_metric("Parse Failed", str(failed), "files needing attention"),
            "</section>",
            '<section class="panel">',
            "<h2>Paper Results</h2>",
            '<div class="table-wrap">',
            "<table>",
            "<thead>",
            "<tr><th>Paper</th><th>Status</th><th>Verdict</th><th>Confidence</th><th>Evidence</th><th>Claims</th><th>Findings</th><th>Top Risks</th><th>Report</th></tr>",
            "</thead>",
            f"<tbody>{rows}</tbody>",
            "</table>",
            "</div>",
            "</section>",
            '<section class="panel compact">',
            "<h2>Included Files</h2>",
            "<p>Use <code>batch-summary.csv</code>, <code>batch-summary.json</code>, or <code>batch-summary.md</code> for machine-readable summaries. Per-paper reports live under <code>reports/&lt;paper&gt;/</code>.</p>",
            "</section>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def render_batch_metric(label: str, value: str, note: str) -> str:
    return f"""
<article class="metric-card">
  <span>{escape(label)}</span>
  <strong>{escape(value)}</strong>
  <small>{escape(note)}</small>
</article>
"""


def render_batch_html_row(item: BatchScanItem, report_stem: str | None) -> str:
    verdict = item.verdict or ("PARSE_FAILED" if item.status == "failed" else "-")
    confidence = f"{item.confidence:.0%}" if item.status == "analyzed" else "-"
    evidence = f"{item.evidence_score:.2f}" if item.status == "analyzed" else "-"
    claims = str(item.claim_count) if item.status == "analyzed" else "-"
    findings = str(item.finding_count) if item.status == "analyzed" else "-"
    risks = "; ".join(item.top_findings) or item.error or "-"
    link = "-"
    if report_stem:
        href = f"reports/{report_stem}/{report_stem}-gauntlet-report.html"
        link = f'<a href="{escape(href, quote=True)}">Open report</a>'
    return f"""
<tr>
  <td>{escape(item.source_name)}</td>
  <td>{escape(item.status)}</td>
  <td><span class="verdict {escape(css_token(verdict))}">{escape(verdict)}</span></td>
  <td>{escape(confidence)}</td>
  <td>{escape(evidence)}</td>
  <td>{escape(claims)}</td>
  <td>{escape(findings)}</td>
  <td>{escape(risks)}</td>
  <td>{link}</td>
</tr>
"""


def build_batch_report_bundle(items: list[BatchScanItem]) -> bytes:
    buffer = BytesIO()
    report_stems = batch_report_stems(items)
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr("index.html", batch_items_to_html(items, report_stems))
        bundle.writestr("batch-summary.csv", batch_items_to_csv(items))
        bundle.writestr("batch-summary.json", batch_items_to_json(items))
        bundle.writestr("batch-summary.md", batch_items_to_markdown(items))
        bundle.writestr("README.txt", batch_bundle_readme(items))

        for item, stem in zip(items, report_stems):
            if not item.report or not stem:
                continue
            bundle.writestr(f"reports/{stem}/{stem}-gauntlet-report.json", item.report.to_json())
            bundle.writestr(f"reports/{stem}/{stem}-gauntlet-report.md", item.report.to_markdown())
            bundle.writestr(f"reports/{stem}/{stem}-gauntlet-report.html", item.report.to_html())
            bundle.writestr(f"reports/{stem}/{stem}-reviewer-action-plan.md", action_plan_to_markdown(item.report))
    return buffer.getvalue()


def batch_bundle_readme(items: list[BatchScanItem]) -> str:
    analyzed = sum(1 for item in items if item.status == "analyzed")
    failed = sum(1 for item in items if item.status == "failed")
    return "\n".join(
        [
            "The Gauntlet Batch Scan Bundle",
            "",
            f"Papers scanned: {len(items)}",
            f"Analyzed: {analyzed}",
            f"Failed: {failed}",
            "",
            "Included files:",
            "- index.html",
            "- batch-summary.csv",
            "- batch-summary.json",
            "- batch-summary.md",
            "- reports/<paper>/<paper>-gauntlet-report.json",
            "- reports/<paper>/<paper>-gauntlet-report.md",
            "- reports/<paper>/<paper>-gauntlet-report.html",
            "- reports/<paper>/<paper>-reviewer-action-plan.md",
            "",
            "Privacy note: this bundle contains deterministic report metadata plus source snippets and anchors already present in each report. It does not include full uploaded paper files or API keys.",
            "",
        ]
    )


def batch_report_stems(items: list[BatchScanItem]) -> list[str | None]:
    used_names: dict[str, int] = {}
    stems: list[str | None] = []
    for item in items:
        if not item.report:
            stems.append(None)
            continue
        stems.append(unique_stem(safe_report_stem(item.source_name), used_names))
    return stems


def unique_stem(stem: str, used_names: dict[str, int]) -> str:
    count = used_names.get(stem, 0) + 1
    used_names[stem] = count
    if count == 1:
        return stem
    return f"{stem}-{count}"


def escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def css_token(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else "-" for character in value).strip("-")


BATCH_INDEX_CSS = """
:root {
  color-scheme: light;
  --ink: #18231f;
  --muted: #60706a;
  --line: #dce5df;
  --paper: #f6f8f5;
  --panel: #ffffff;
  --green: #1f6f4a;
  --amber: #a26313;
  --red: #9b2f2f;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  color: var(--ink);
  background: var(--paper);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.batch-shell {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 40px 0;
}
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 24px;
  align-items: stretch;
  padding: 28px;
  border: 1px solid var(--line);
  background: var(--panel);
}
.eyebrow {
  margin: 0 0 10px;
  color: var(--green);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}
h1, h2, p { margin-top: 0; }
h1 { margin-bottom: 12px; font-size: clamp(2rem, 4vw, 4rem); line-height: 0.98; }
h2 { margin-bottom: 18px; }
p { color: var(--muted); line-height: 1.6; }
.privacy-card, .metric-card, .panel {
  border: 1px solid var(--line);
  background: var(--panel);
}
.privacy-card {
  display: flex;
  min-height: 180px;
  flex-direction: column;
  justify-content: center;
  padding: 20px;
}
.privacy-card span, .metric-card span {
  color: var(--muted);
  font-size: 0.76rem;
  font-weight: 800;
  text-transform: uppercase;
}
.privacy-card strong {
  margin: 8px 0;
  font-size: 1.4rem;
}
.privacy-card small, .metric-card small { color: var(--muted); }
.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin: 16px 0;
}
.metric-card { padding: 18px; }
.metric-card strong {
  display: block;
  margin: 8px 0;
  font-size: 2rem;
}
.panel {
  margin-top: 16px;
  padding: 24px;
}
.panel.compact { padding-bottom: 14px; }
.table-wrap { overflow-x: auto; }
table {
  width: 100%;
  border-collapse: collapse;
  min-width: 920px;
}
th, td {
  padding: 12px 10px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}
th {
  color: var(--muted);
  font-size: 0.78rem;
  text-transform: uppercase;
}
a {
  color: var(--green);
  font-weight: 800;
}
.verdict {
  display: inline-flex;
  padding: 4px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 900;
}
.verdict.resolves { color: var(--green); border-color: #b9d7c4; background: #ecf8ef; }
.verdict.partial { color: var(--amber); border-color: #e8c48e; background: #fff7e8; }
.verdict.fails, .verdict.creates-new-paradoxes, .verdict.parse-failed {
  color: var(--red);
  border-color: #e4aaa1;
  background: #fff0ee;
}
code {
  padding: 2px 5px;
  border: 1px solid var(--line);
  background: #f0f4ef;
}
@media (max-width: 780px) {
  .hero { grid-template-columns: 1fr; }
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
"""
