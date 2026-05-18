from __future__ import annotations

import json
from zipfile import ZipFile

from gauntlet_core import analyze_paper_text
from gauntlet_core.batch import (
    BatchScanItem,
    batch_items_to_csv,
    batch_items_to_json,
    batch_items_to_markdown,
    build_batch_report_bundle,
    failed_batch_item,
    filter_batch_items,
    sort_batch_items,
    summarize_report,
)


def test_batch_summary_exports_include_expected_fields(tmp_path):
    report = analyze_paper_text(
        "The framework resolves the anomaly because the mechanism uses 12 measured observations.",
        source_name="paper.txt",
    )
    items = [summarize_report(report), failed_batch_item("bad.pdf", "No readable text")]

    csv_text = batch_items_to_csv(items)
    json_text = batch_items_to_json(items)
    markdown = batch_items_to_markdown(items)

    assert "source_name,status,verdict" in csv_text
    assert "paper.txt,analyzed" in csv_text
    assert json.loads(json_text)[1]["status"] == "failed"
    assert "The Gauntlet Batch Scan" in markdown
    assert "bad.pdf" in markdown

    bundle_path = tmp_path / "batch.zip"
    bundle_path.write_bytes(build_batch_report_bundle(items))
    with ZipFile(bundle_path) as archive:
        names = set(archive.namelist())
        assert "batch-summary.csv" in names
        assert "batch-summary.json" in names
        assert "batch-summary.md" in names
        assert "README.txt" in names
        assert "reports/paper/paper-gauntlet-report.html" in names
        assert "reports/paper/paper-reviewer-action-plan.md" in names


def test_batch_filter_and_sort_helpers():
    items = [
        BatchScanItem("resolved.txt", "analyzed", verdict="RESOLVES", confidence=0.82, evidence_score=0.72),
        BatchScanItem(
            "weak.txt",
            "analyzed",
            verdict="FAILS",
            confidence=0.41,
            evidence_score=0.18,
            finding_count=4,
            high_severity_findings=1,
        ),
        failed_batch_item("broken.pdf", "No readable text"),
    ]

    assert [item.source_name for item in filter_batch_items(items, verdicts={"FAILS"})] == ["weak.txt"]
    assert [item.source_name for item in filter_batch_items(items, verdicts={"PARSE_FAILED"})] == ["broken.pdf"]
    assert {item.source_name for item in filter_batch_items(items, high_risk_only=True)} == {"weak.txt", "broken.pdf"}
    assert [item.source_name for item in filter_batch_items(items, weak_evidence_only=True)] == ["weak.txt"]
    assert [item.source_name for item in sort_batch_items(items, "Highest risk")] == [
        "broken.pdf",
        "weak.txt",
        "resolved.txt",
    ]
