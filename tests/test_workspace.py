import json

from gauntlet_core import AnalysisReport, analyze_paper_text
from gauntlet_core.benchmarks import run_benchmark_sample
from gauntlet_core.repair_workshop import build_repair_steps
from gauntlet_core.revision_recheck import recheck_repair_revision
from gauntlet_core.workspace import (
    delete_saved_run,
    list_saved_runs,
    load_saved_run,
    save_analysis_run,
    update_saved_run_revision_recheck,
    update_saved_run_repair_progress,
    update_saved_run_issue_review,
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
    assert loaded.repair_progress == {}
    assert loaded.revision_rechecks == {}
    assert loaded.issue_reviews == {}
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


def test_workspace_saves_repair_progress_without_raw_paper_or_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("GAUNTLET_WORKSPACE_DIR", str(tmp_path / "runs"))
    report = analyze_paper_text(
        "The paper resolves the paradox and eliminates the contradiction.",
        source_name="repair-progress.txt",
    )

    saved = save_analysis_run(report, "analysis")
    updated = update_saved_run_repair_progress(saved.run_id, "RTEST123", "fixed", "Mechanism paragraph added.")
    loaded = load_saved_run(saved.run_id)
    payload = json.loads((tmp_path / "runs" / f"{saved.run_id}.json").read_text(encoding="utf-8"))

    assert updated.repair_progress["RTEST123"]["status"] == "fixed"
    assert loaded.repair_progress["RTEST123"]["reviewer_note"] == "Mechanism paragraph added."
    assert list_saved_runs()[0].repair_progress_counts["fixed"] == 1
    assert payload["repair_progress"]["RTEST123"]["status"] == "fixed"
    assert "api_key" not in json.dumps(payload).lower()
    assert "paper_text" not in payload


def test_workspace_saves_issue_reviews_without_raw_paper_or_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("GAUNTLET_WORKSPACE_DIR", str(tmp_path / "runs"))
    report = analyze_paper_text(
        "The paper resolves the paradox and eliminates the contradiction.",
        source_name="issue-review.txt",
    )

    saved = save_analysis_run(report, "analysis")
    updated = update_saved_run_issue_review(saved.run_id, "F1", "false-positive", "Prior-work comparison, not this paper's claim.")
    loaded = load_saved_run(saved.run_id)
    payload = json.loads((tmp_path / "runs" / f"{saved.run_id}.json").read_text(encoding="utf-8"))

    assert updated.issue_reviews["F1"]["status"] == "false-positive"
    assert loaded.issue_reviews["F1"]["reviewer_note"] == "Prior-work comparison, not this paper's claim."
    assert list_saved_runs()[0].issue_review_counts["false-positive"] == 1
    assert payload["issue_reviews"]["F1"]["status"] == "false-positive"
    assert "api_key" not in json.dumps(payload).lower()
    assert "paper_text" not in payload


def test_workspace_loads_older_saved_runs_without_repair_progress(tmp_path, monkeypatch):
    monkeypatch.setenv("GAUNTLET_WORKSPACE_DIR", str(tmp_path / "runs"))
    report = analyze_paper_text("The framework explains the issue because the mechanism is measured.", source_name="old.txt")
    saved = save_analysis_run(report, "analysis")
    path = tmp_path / "runs" / f"{saved.run_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("repair_progress", None)
    payload.pop("revision_rechecks", None)
    payload.pop("issue_reviews", None)
    payload["schema_version"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_saved_run(saved.run_id)

    assert loaded.repair_progress == {}
    assert loaded.revision_rechecks == {}
    assert loaded.issue_reviews == {}
    assert list_saved_runs()[0].repair_progress_counts == {}
    assert list_saved_runs()[0].revision_recheck_counts == {}
    assert list_saved_runs()[0].issue_review_counts == {}


def test_workspace_saves_revision_recheck_without_raw_paper_or_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("GAUNTLET_WORKSPACE_DIR", str(tmp_path / "runs"))
    report = analyze_paper_text("The paper resolves the paradox and eliminates the contradiction.", source_name="revision-run.txt")
    saved = save_analysis_run(report, "analysis")
    step = build_repair_steps(report)[0]
    result = recheck_repair_revision(
        report,
        step,
        "The paper resolves the paradox because a specific mechanism links the contradiction to 12 measured observations.",
    )

    updated = update_saved_run_revision_recheck(saved.run_id, result)
    loaded = load_saved_run(saved.run_id)
    payload = json.loads((tmp_path / "runs" / f"{saved.run_id}.json").read_text(encoding="utf-8"))

    assert updated.revision_rechecks[step.id]["status"] == result.status
    assert loaded.revision_rechecks[step.id]["revised_text"] == result.revised_text
    assert list_saved_runs()[0].revision_recheck_counts[result.status] == 1
    assert payload["revision_rechecks"][step.id]["step_id"] == step.id
    assert "api_key" not in json.dumps(payload).lower()
    assert "paper_text" not in payload


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
