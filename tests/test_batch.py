from __future__ import annotations

import json
from zipfile import ZipFile

from gauntlet_core import analyze_paper_text
from gauntlet_core.batch import (
    batch_items_to_csv,
    batch_items_to_json,
    batch_items_to_markdown,
    build_batch_report_bundle,
    failed_batch_item,
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
