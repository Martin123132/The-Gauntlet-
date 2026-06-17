import json

from gauntlet_core.system_check import collect_system_check


def test_system_check_reports_runtime_and_export_data(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for filename in ("Start-Gauntlet.bat", "requirements.txt", "app.py", "README.md", "requirements-ai.txt"):
        (repo / filename).write_text("placeholder", encoding="utf-8")
    log_dir = repo / ".gauntlet" / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "Start-Gauntlet.log").write_text("launcher log", encoding="utf-8")
    workspace = repo / ".gauntlet" / "workspace" / "runs"
    workspace.mkdir(parents=True)

    report = collect_system_check(repo_path=repo, workspace_path=workspace)
    payload = json.loads(report.to_json())
    markdown = report.to_markdown()

    assert report.app_version
    assert report.overall_status in {"ok", "warn", "fail"}
    assert payload["repo_path"] == str(repo.resolve())
    assert payload["workspace_path"] == str(workspace.resolve())
    assert payload["ocr_readiness"]["status"] in {"available", "partial", "not_installed"}
    assert "The Gauntlet System Check" in markdown
    assert "OCR readiness" in markdown
    assert "Start-Gauntlet.bat" in markdown
    assert "uploaded paper files" in markdown
    assert any(item.name == "Launcher log" and item.status == "ok" for item in report.items)
    assert any(item.name == "Optional OCR readiness" for item in report.items)


def test_system_check_surfaces_missing_public_files(tmp_path):
    report = collect_system_check(repo_path=tmp_path, workspace_path=tmp_path / "runs")

    missing = [item for item in report.items if item.name.startswith("Required file:") and item.status == "fail"]
    assert missing
    assert report.overall_status == "fail"
