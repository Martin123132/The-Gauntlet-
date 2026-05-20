from streamlit.testing.v1 import AppTest
import pytest

import app as gauntlet_app
from gauntlet_core import analyze_paper_text
from gauntlet_core.batch import BatchScanItem
from gauntlet_core.workspace import list_saved_runs, load_saved_run, save_analysis_run


@pytest.fixture(autouse=True)
def isolate_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("GAUNTLET_WORKSPACE_DIR", str(tmp_path / "runs"))


def test_streamlit_app_renders_primary_controls():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)

    assert not app.exception
    assert app.file_uploader
    assert any(button.label == "Analyze Paper" for button in app.button)
    assert any("The Gauntlet" in item.value for item in app.markdown)


def test_streamlit_sample_workflow_produces_report():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)
    app.toggle[0].set_value(True)
    app.button[0].click()
    app.run(timeout=20)

    assert not app.exception
    report = app.session_state["report"]
    assert report.verdict in {"RESOLVES", "PARTIAL", "FAILS", "CREATES_NEW_PARADOXES"}
    assert "The Gauntlet Report" in report.to_markdown()
    assert list_saved_runs()


def test_streamlit_breakdown_page_keeps_report_state():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)
    app.toggle[0].set_value(True)
    app.button[0].click()
    app.run(timeout=20)

    app.query_params["page"] = "breakdown"
    app.run(timeout=20)

    assert not app.exception
    assert any("Actual Breakdown" in item.value for item in app.markdown)
    assert any("Claim-by-Claim Audit" in item.value for item in app.markdown)
    assert any("Curtain-Up Audit" in item.value for item in app.markdown)
    assert any("Source Trace" in item.value for item in app.markdown)
    assert any("Source for" in expander.label for expander in app.expander)


def test_streamlit_refinement_page_is_locked_without_session_keys():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)
    app.toggle[0].set_value(True)
    app.button[0].click()
    app.run(timeout=20)

    app.query_params["page"] = "refinement"
    app.run(timeout=20)

    assert not app.exception
    assert any("Optional Refinement Chamber" in item.value for item in app.markdown)
    assert any("Run Curtain-Up Refinement" == button.label for button in app.button)


def test_streamlit_claims_and_evidence_pages_show_source_references():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)
    app.toggle[0].set_value(True)
    app.button[0].click()
    app.run(timeout=20)

    app.query_params["page"] = "claims"
    app.run(timeout=20)

    assert not app.exception
    assert any("Source for C" in expander.label for expander in app.expander)

    app.query_params["page"] = "evidence"
    app.run(timeout=20)

    assert not app.exception
    assert any("Source Trace" in item.value for item in app.markdown)


def test_streamlit_repair_workshop_page_saves_progress():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)
    app.toggle[0].set_value(True)
    app.button[0].click()
    app.run(timeout=20)

    app.query_params["page"] = "action"
    app.run(timeout=20)

    assert not app.exception
    assert any("Repair Workshop" in item.value for item in app.markdown)
    assert any("Repair filter" == radio.label for radio in app.radio)
    assert any("Save Repair Progress" == button.label for button in app.button)

    status_box = next(selectbox for selectbox in app.selectbox if selectbox.label == "Repair status")
    status_box.set_value("in-progress")
    note_box = next(area for area in app.text_area if area.label == "Reviewer note")
    note_box.set_value("Working on the mechanism paragraph.")
    save_button = next(button for button in app.button if button.label == "Save Repair Progress")
    save_button.click()
    app.run(timeout=20)

    saved_run = load_saved_run(app.session_state["workspace_run_id"])
    assert any(item["status"] == "in-progress" for item in saved_run.repair_progress.values())
    assert any("mechanism paragraph" in item["reviewer_note"] for item in saved_run.repair_progress.values())


def test_streamlit_source_viewer_highlights_selected_anchor():
    app = AppTest.from_file("app.py")
    app.run(timeout=20)
    app.toggle[0].set_value(True)
    app.button[0].click()
    app.run(timeout=20)

    anchor_id = app.session_state["report"].source_spans[0].anchor_id
    app.query_params["page"] = "source"
    app.query_params["anchor"] = anchor_id
    app.run(timeout=20)

    assert not app.exception
    assert any("Source Review" in item.value for item in app.markdown)
    assert any("Issue Queue" in item.value for item in app.markdown)
    assert any("Highlighted Source" in item.value for item in app.markdown)
    assert any("Rule Explanation & Repair" in item.value for item in app.markdown)
    assert any("Linked Audit Items" in item.value for item in app.markdown)
    assert any("Source anchor" == selectbox.label for selectbox in app.selectbox)
    assert any("Issue filter" == radio.label for radio in app.radio)

    if len(app.session_state["report"].source_spans) > 1:
        second_anchor_id = app.session_state["report"].source_spans[1].anchor_id
        app.query_params["anchor"] = second_anchor_id
        app.run(timeout=20)

        assert not app.exception
        assert any(f"Highlighted source sentence | {second_anchor_id}" in item.value for item in app.markdown)


def test_streamlit_benchmarks_page_runs_sample_and_compares_results():
    app = AppTest.from_file("app.py")
    app.query_params["page"] = "benchmarks"
    app.run(timeout=20)

    assert not app.exception
    assert any("Benchmark Demo Gallery" in item.value for item in app.markdown)
    run_button = next(button for button in app.button if button.label == "Run Benchmark Sample")
    run_button.click()
    app.run(timeout=20)

    assert not app.exception
    assert app.session_state["benchmark_result"].passed
    assert app.session_state["report"].source_name.startswith("benchmark-")
    assert any("Expected vs Actual" in item.value for item in app.markdown)
    assert any("Guarded Findings Kept Out" in item.value for item in app.markdown)
    assert "The Gauntlet Benchmark" in app.session_state["benchmark_result"].to_markdown()


def test_streamlit_batch_page_renders_controls():
    app = AppTest.from_file("app.py")
    app.query_params["page"] = "batch"
    app.run(timeout=20)

    assert not app.exception
    assert any("Batch Scan" in item.value for item in app.markdown)
    assert any("Run Batch Scan" == button.label for button in app.button)
    assert any("Load Demo Batch" == button.label for button in app.button)
    assert app.file_uploader

    demo_button = next(button for button in app.button if button.label == "Load Demo Batch")
    demo_button.click()
    app.run(timeout=30)

    assert not app.exception
    assert len(app.session_state["batch_items"]) >= 8
    assert list_saved_runs()
    assert any("Filter & Sort" in item.value for item in app.markdown)


def test_streamlit_share_demo_page_renders_share_kit():
    app = AppTest.from_file("app.py")
    app.query_params["page"] = "share"
    app.run(timeout=20)

    assert not app.exception
    assert any("Share Demo Kit" in item.value for item in app.markdown)
    assert any("X Post Draft" in item.value for item in app.markdown)
    assert any("synthetic benchmark papers only" in item.value for item in app.markdown)


def test_streamlit_workspace_page_lists_opens_compares_and_deletes(tmp_path, monkeypatch):
    monkeypatch.setenv("GAUNTLET_WORKSPACE_DIR", str(tmp_path / "runs"))
    app = AppTest.from_file("app.py")
    app.run(timeout=20)
    app.toggle[0].set_value(True)
    app.button[0].click()
    app.run(timeout=20)
    second_report = analyze_paper_text(
        "The theory explains the anomaly because the model says the result follows.",
        source_name="second-paper.txt",
    )
    save_analysis_run(second_report, "analysis")

    app.query_params["page"] = "workspace"
    app.run(timeout=20)

    assert not app.exception
    assert len(list_saved_runs()) == 2
    assert any("Saved Workspace" in item.value for item in app.markdown)
    assert any("Compare Saved Runs" in item.value for item in app.markdown)
    assert any("Repair progress" in item.value for item in app.markdown)

    open_button = next(button for button in app.button if button.label == "Open Saved Run")
    open_button.click()
    app.run(timeout=20)

    assert "report" in app.session_state

    app.query_params["page"] = "source"
    app.run(timeout=20)

    assert not app.exception
    assert any("Source Review" in item.value for item in app.markdown)
    assert any("Issue Queue" in item.value for item in app.markdown)

    app.query_params["page"] = "workspace"
    app.run(timeout=20)

    before_delete = len(list_saved_runs())
    delete_button = next(button for button in app.button if button.label == "Delete Saved Run")
    delete_button.click()
    app.run(timeout=20)

    assert len(list_saved_runs()) == before_delete - 1


def test_render_exports_registers_html_download(monkeypatch):
    report = analyze_paper_text(
        "The framework resolves the anomaly because the mechanism uses 12 measured observations.",
        source_name="export-paper.txt",
    )
    calls = []

    class FakeColumn:
        def download_button(self, label, **kwargs):
            calls.append((label, kwargs))

    class FakeStreamlit:
        def columns(self, count):
            return [FakeColumn() for _ in range(count)]

    monkeypatch.setattr(gauntlet_app, "st", FakeStreamlit())

    gauntlet_app.render_exports(report)

    labels = [label for label, _ in calls]
    assert labels == ["Export JSON", "Export Markdown", "Export HTML Report", "Export Report Bundle"]
    assert calls[2][1]["mime"] == "text/html"
    assert calls[2][1]["file_name"].endswith("-gauntlet-report.html")
    assert calls[-1][1]["mime"] == "application/zip"
    assert calls[-1][1]["file_name"].endswith("-gauntlet-report-bundle.zip")


def test_batch_filter_controls_apply_selected_view(monkeypatch):
    items = [
        BatchScanItem("resolved.txt", "analyzed", verdict="RESOLVES", confidence=0.9, evidence_score=0.8),
        BatchScanItem("failed.txt", "analyzed", verdict="FAILS", confidence=0.3, evidence_score=0.1, finding_count=3),
    ]

    class FakeColumn:
        def multiselect(self, label, options, default=None):
            return ["FAILS"]

        def checkbox(self, label):
            return False

        def selectbox(self, label, options):
            return "Most findings"

    class FakeStreamlit:
        def markdown(self, *args, **kwargs):
            return None

        def columns(self, spec):
            return [FakeColumn(), FakeColumn(), FakeColumn()]

    monkeypatch.setattr(gauntlet_app, "st", FakeStreamlit())

    visible = gauntlet_app.render_batch_filter_controls(items)

    assert [item.source_name for item in visible] == ["failed.txt"]
