from streamlit.testing.v1 import AppTest


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
    assert "The Gauntlet Benchmark" in app.session_state["benchmark_result"].to_markdown()
