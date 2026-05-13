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
