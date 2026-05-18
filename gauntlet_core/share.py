from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from html import escape
from io import BytesIO
import json
from zipfile import ZIP_DEFLATED, ZipFile

from .batch import (
    BatchScanItem,
    batch_items_to_csv,
    batch_items_to_html,
    batch_items_to_json,
    batch_items_to_markdown,
    build_batch_report_bundle,
    build_demo_batch_items,
)


DEFAULT_REPO_URL = "https://github.com/Martin123132/The-Gauntlet-"


@dataclass(frozen=True)
class DemoShareSummary:
    paper_count: int
    analyzed_count: int
    high_risk_count: int
    avg_evidence: float
    verdict_counts: dict[str, int]
    top_findings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "paper_count": self.paper_count,
            "analyzed_count": self.analyzed_count,
            "high_risk_count": self.high_risk_count,
            "avg_evidence": round(self.avg_evidence, 4),
            "verdict_counts": self.verdict_counts,
            "top_findings": list(self.top_findings),
        }


def build_demo_share_summary(items: list[BatchScanItem] | None = None) -> DemoShareSummary:
    items = items or build_demo_batch_items()
    analyzed = [item for item in items if item.status == "analyzed"]
    high_risk_count = sum(
        1
        for item in items
        if item.status == "failed" or item.high_severity_findings > 0 or item.verdict in {"FAILS", "CREATES_NEW_PARADOXES"}
    )
    avg_evidence = sum(item.evidence_score for item in analyzed) / len(analyzed) if analyzed else 0.0
    verdict_counts = dict(Counter(item.verdict or "PARSE_FAILED" for item in items))
    finding_counts: Counter[str] = Counter()
    for item in items:
        finding_counts.update(item.top_findings)
    top_findings = tuple(finding for finding, _ in finding_counts.most_common(5))
    return DemoShareSummary(
        paper_count=len(items),
        analyzed_count=len(analyzed),
        high_risk_count=high_risk_count,
        avg_evidence=avg_evidence,
        verdict_counts=verdict_counts,
        top_findings=top_findings,
    )


def build_x_post(repo_url: str = DEFAULT_REPO_URL) -> str:
    return (
        "The Gauntlet is now a local non-AI paper checker demo: download the repo, "
        "double-click Start-Gauntlet.bat, upload papers, and get transparent verdicts "
        f"with claims, evidence, and contradictions. {repo_url}"
    )


def build_x_thread(repo_url: str = DEFAULT_REPO_URL) -> str:
    return "\n\n".join(
        [
            build_x_post(repo_url),
            "It runs locally first: no API key needed for the default checker. Optional AI refinement is separate.",
            "The demo batch uses synthetic benchmark papers so people can see the rules catch weak evidence, contradictions, scope conflicts, circular support, and theory-as-fact language.",
            "The exported batch bundle includes an offline HTML index, CSV/JSON/Markdown summaries, per-paper reports, and source snippets for auditability.",
        ]
    )


def build_share_card_html(summary: DemoShareSummary | None = None, repo_url: str = DEFAULT_REPO_URL) -> str:
    summary = summary or build_demo_share_summary()
    metrics = [
        ("Demo Papers", str(summary.paper_count)),
        ("Analyzed", str(summary.analyzed_count)),
        ("High Risk", str(summary.high_risk_count)),
        ("Avg Evidence", f"{summary.avg_evidence:.2f}"),
    ]
    metric_html = "".join(f"<div><span>{escape(label)}</span><strong>{escape(value)}</strong></div>" for label, value in metrics)
    findings = ", ".join(summary.top_findings) or "No top findings"
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>The Gauntlet Share Card</title>",
            f"<style>{SHARE_CARD_CSS}</style>",
            "</head>",
            "<body>",
            '<main class="share-card">',
            '<p class="eyebrow">The Gauntlet</p>',
            "<h1>Local Non-AI Paper Checker</h1>",
            "<p>Upload papers, get transparent verdicts, inspect claims, evidence, contradictions, source anchors, benchmarks, and batch exports.</p>",
            f'<section class="metrics">{metric_html}</section>',
            f'<p class="findings">Demo catches: {escape(findings)}</p>',
            f'<p class="repo">{escape(repo_url)}</p>',
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def build_share_card_svg(summary: DemoShareSummary | None = None, repo_url: str = DEFAULT_REPO_URL) -> str:
    summary = summary or build_demo_share_summary()
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">
  <rect width="1200" height="675" fill="#f6f8f5"/>
  <rect x="54" y="54" width="1092" height="567" fill="#ffffff" stroke="#dce5df" stroke-width="2"/>
  <text x="96" y="125" fill="#1f6f4a" font-family="Arial, sans-serif" font-size="26" font-weight="700">THE GAUNTLET</text>
  <text x="96" y="214" fill="#18231f" font-family="Arial, sans-serif" font-size="72" font-weight="800">Local Non-AI</text>
  <text x="96" y="296" fill="#18231f" font-family="Arial, sans-serif" font-size="72" font-weight="800">Paper Checker</text>
  <text x="96" y="365" fill="#60706a" font-family="Arial, sans-serif" font-size="30">Transparent verdicts for claims, evidence, contradictions,</text>
  <text x="96" y="407" fill="#60706a" font-family="Arial, sans-serif" font-size="30">source anchors, benchmarks, and batch exports.</text>
  <rect x="96" y="464" width="210" height="98" fill="#ecf8ef" stroke="#b9d7c4"/>
  <rect x="330" y="464" width="210" height="98" fill="#fff7e8" stroke="#e8c48e"/>
  <rect x="564" y="464" width="210" height="98" fill="#fff0ee" stroke="#e4aaa1"/>
  <rect x="798" y="464" width="210" height="98" fill="#f0f4ef" stroke="#dce5df"/>
  <text x="120" y="504" fill="#60706a" font-family="Arial, sans-serif" font-size="20" font-weight="700">DEMO PAPERS</text>
  <text x="120" y="546" fill="#18231f" font-family="Arial, sans-serif" font-size="40" font-weight="800">{summary.paper_count}</text>
  <text x="354" y="504" fill="#60706a" font-family="Arial, sans-serif" font-size="20" font-weight="700">ANALYZED</text>
  <text x="354" y="546" fill="#18231f" font-family="Arial, sans-serif" font-size="40" font-weight="800">{summary.analyzed_count}</text>
  <text x="588" y="504" fill="#60706a" font-family="Arial, sans-serif" font-size="20" font-weight="700">HIGH RISK</text>
  <text x="588" y="546" fill="#18231f" font-family="Arial, sans-serif" font-size="40" font-weight="800">{summary.high_risk_count}</text>
  <text x="822" y="504" fill="#60706a" font-family="Arial, sans-serif" font-size="20" font-weight="700">AVG EVIDENCE</text>
  <text x="822" y="546" fill="#18231f" font-family="Arial, sans-serif" font-size="40" font-weight="800">{summary.avg_evidence:.2f}</text>
  <text x="96" y="600" fill="#60706a" font-family="Arial, sans-serif" font-size="22">{escape(repo_url)}</text>
</svg>
"""


def build_demo_share_readme(repo_url: str = DEFAULT_REPO_URL) -> str:
    return "\n".join(
        [
            "# The Gauntlet Demo Share Pack",
            "",
            "This pack is generated from synthetic benchmark papers. It is meant for public demo posts and does not include private uploaded documents.",
            "",
            "## Files",
            "",
            "- `x-post.txt`: a short X post draft.",
            "- `x-thread.md`: a longer thread draft.",
            "- `share-card.html`: screenshot-ready social card.",
            "- `share-card.svg`: static social card source.",
            "- `demo-batch-index.html`: offline batch dashboard.",
            "- `demo-batch-summary.csv`, `.json`, `.md`: machine-readable demo summaries.",
            "- `gauntlet-demo-batch-bundle.zip`: full demo batch report bundle with per-paper reports.",
            "- `demo-share-summary.json`: metrics used by the card and drafts.",
            "",
            "## Suggested Flow",
            "",
            "1. Open `share-card.html` or `share-card.svg` and screenshot it.",
            "2. Paste `x-post.txt` into X.",
            "3. Add the screenshot and the repo link.",
            "4. Keep the bundle available for anyone who wants to inspect the deterministic reports.",
            "",
            f"Repo: {repo_url}",
            "",
        ]
    )


def build_demo_share_pack(repo_url: str = DEFAULT_REPO_URL) -> bytes:
    items = build_demo_batch_items()
    summary = build_demo_share_summary(items)
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr("README.md", build_demo_share_readme(repo_url))
        bundle.writestr("x-post.txt", build_x_post(repo_url))
        bundle.writestr("x-thread.md", build_x_thread(repo_url))
        bundle.writestr("share-card.html", build_share_card_html(summary, repo_url))
        bundle.writestr("share-card.svg", build_share_card_svg(summary, repo_url))
        bundle.writestr("demo-batch-index.html", batch_items_to_html(items))
        bundle.writestr("demo-batch-summary.csv", batch_items_to_csv(items))
        bundle.writestr("demo-batch-summary.json", batch_items_to_json(items))
        bundle.writestr("demo-batch-summary.md", batch_items_to_markdown(items))
        bundle.writestr("demo-share-summary.json", json.dumps(summary.to_dict(), indent=2))
        bundle.writestr("gauntlet-demo-batch-bundle.zip", build_batch_report_bundle(items))
    return buffer.getvalue()


SHARE_CARD_CSS = """
:root {
  color-scheme: light;
  --ink: #18231f;
  --muted: #60706a;
  --line: #dce5df;
  --paper: #f6f8f5;
  --panel: #ffffff;
  --green: #1f6f4a;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: var(--paper);
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.share-card {
  width: min(1200px, calc(100vw - 32px));
  aspect-ratio: 16 / 9;
  padding: clamp(32px, 6vw, 72px);
  border: 1px solid var(--line);
  background: var(--panel);
}
.eyebrow {
  margin: 0 0 20px;
  color: var(--green);
  font-size: clamp(1rem, 2vw, 1.7rem);
  font-weight: 900;
  text-transform: uppercase;
}
h1 {
  max-width: 820px;
  margin: 0 0 20px;
  font-size: clamp(3rem, 8vw, 6.5rem);
  line-height: 0.95;
}
p {
  max-width: 940px;
  color: var(--muted);
  font-size: clamp(1.1rem, 2vw, 1.9rem);
  line-height: 1.35;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 38px 0 20px;
}
.metrics div {
  min-height: 98px;
  padding: 16px;
  border: 1px solid var(--line);
  background: #f9fbf8;
}
.metrics span {
  display: block;
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 900;
  text-transform: uppercase;
}
.metrics strong {
  display: block;
  margin-top: 8px;
  font-size: clamp(2rem, 4vw, 3rem);
}
.findings, .repo {
  margin-bottom: 0;
  font-size: clamp(0.95rem, 1.5vw, 1.25rem);
}
"""
