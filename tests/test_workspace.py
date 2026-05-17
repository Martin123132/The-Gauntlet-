import json

from gauntlet_core import AnalysisReport, analyze_paper_text
from gauntlet_core.benchmarks import run_benchmark_sample
from gauntlet_core.workspace import (
    delete_saved_run,
    list_saved_runs,
    load_saved_run,
    save_analysis_run,
    update_saved_run_notes,
)


def test_workspace_save_list_load_update_and_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("GAUNTLET_WORKSPACE_DIR", str(tmp_path / "runs"))
    report = analyze_paper_text(
        "The framework resolves the paradox because the mechanism is measured by 12 observations.",
        source_name="paper.txt",
    )

    saved = save_analysis_run(report, "analysis")
    summaries = list_saved_runs()
    loaded = load_saved_run(saved.run_id)
    updated = update_saved_run_notes(saved.run_id, "Reviewer confirmed the mechanism gap.", "confirmed")

    assert len(summaries) == 1
    assert summaries[0].source_name == "paper.txt"
    assert loaded.report.source_name == "paper.txt"
    assert loaded.report.claims[0].source_span is not None
    assert updated.review_status == "confirmed"
    assert updated.notes == "Reviewer confirmed the mechanism gap."

    delete_saved_run(saved.run_id)

    assert list_saved_runs() == []


def test_saved_run_does_not_store_raw_paper_text_or_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("GAUNTLET_WORKSPACE_DIR", str(tmp_path / "runs"))
    report = analyze_paper_text(
        "The paper resolves the anomaly because the mechanism is measured by equation x = 1. "
        "This extra sentence is source-trace text, not a saved document blob.",
        source_name="privacy.txt",
    )

    saved = save_analysis_run(report, "analysis")
    saved_path = tmp_path / "runs" / f"{saved.run_id}.json"
    payload = json.loads(saved_path.read_text(encoding="utf-8"))
    serialized = saved_path.read_text(encoding="utf-8").lower()

    assert "paper_text" not in payload
    assert "source_text" not in payload
    assert payload["report"]["source_spans"]
    assert "api_key" not in serialized
    assert "sk-" not in serialized


def test_analysis_report_round_trips_from_dict():
    report = analyze_paper_text(
        "The framework resolves the paradox because the mechanism is measured by 12 observations.",
        source_name="round-trip.txt",
    )

    restored = AnalysisReport.from_dict(report.to_dict())

    assert restored.source_name == report.source_name
    assert restored.verdict == report.verdict
    assert restored.claims[0].source_span is not None
    assert restored.evidence.evidence_links[0].source_span is not None
    assert restored.to_markdown().startswith("# The Gauntlet Report")


def test_benchmark_saved_run_stores_metadata_without_sample_text(tmp_path, monkeypatch):
    monkeypatch.setenv("GAUNTLET_WORKSPACE_DIR", str(tmp_path / "runs"))
    comparison = run_benchmark_sample("strong-mechanism-evidence")

    saved = save_analysis_run(comparison.report, "benchmark", benchmark_result=comparison)
    payload = json.loads((tmp_path / "runs" / f"{saved.run_id}.json").read_text(encoding="utf-8"))

    assert payload["benchmark"]["sample_id"] == "strong-mechanism-evidence"
    assert payload["benchmark"]["expected_verdict"] == "RESOLVES"
    assert "paper_text" not in payload["benchmark"]
    assert "The framework resolves the anomaly through a geometric mechanism" not in json.dumps(payload["benchmark"])
