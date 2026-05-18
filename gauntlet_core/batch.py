from __future__ import annotations

import csv
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


def build_batch_report_bundle(items: list[BatchScanItem]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr("batch-summary.csv", batch_items_to_csv(items))
        bundle.writestr("batch-summary.json", batch_items_to_json(items))
        bundle.writestr("batch-summary.md", batch_items_to_markdown(items))
        bundle.writestr("README.txt", batch_bundle_readme(items))

        used_names: dict[str, int] = {}
        for item in items:
            if not item.report:
                continue
            stem = unique_stem(safe_report_stem(item.source_name), used_names)
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


def unique_stem(stem: str, used_names: dict[str, int]) -> str:
    count = used_names.get(stem, 0) + 1
    used_names[stem] = count
    if count == 1:
        return stem
    return f"{stem}-{count}"


def escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
