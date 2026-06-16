import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_release_files_exist():
    required_paths = [
        "README.md",
        "LICENSE",
        "Start-Gauntlet.bat",
        "Analyze-Paper.bat",
        "requirements.txt",
        "requirements-ai.txt",
        "result-packs/README.md",
        "result-packs/landmark-paper-starter.json",
        "docs/RELEASE_CHECKLIST.md",
        "docs/images/gauntlet-summary.png",
        "docs/images/gauntlet-breakdown.png",
        "docs/images/gauntlet-workspace.png",
        "docs/images/gauntlet-source-viewer.png",
        "docs/images/gauntlet-benchmarks.png",
        "docs/images/gauntlet-refinement.png",
        ".github/workflows/tests.yml",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/benchmark_idea.yml",
        ".github/ISSUE_TEMPLATE/false_positive.yml",
    ]

    missing = [path for path in required_paths if not (ROOT / path).exists()]

    assert not missing


def test_windows_launcher_keeps_default_install_non_ai():
    launcher = (ROOT / "Start-Gauntlet.bat").read_text(encoding="utf-8")
    command_lines = [
        line.strip().lower()
        for line in launcher.splitlines()
        if line.strip() and not line.strip().lower().startswith("echo")
    ]

    assert any("python 3.10" in line.lower() for line in launcher.splitlines())
    assert any("pip install -r requirements.txt" in line for line in command_lines)
    assert not any("pip install -r requirements-ai.txt" in line for line in command_lines)
    assert "requirements-ai.txt" in launcher
    assert "http://localhost:8501" in launcher
    assert ".gauntlet\\logs" in launcher
    assert "Launcher log:" in launcher
    assert "Repo folder:" in launcher
    assert "Venv folder:" in launcher
    assert "Streamlit stopped before The Gauntlet could open." in launcher


def test_drag_drop_analyzer_keeps_default_install_non_ai():
    launcher = (ROOT / "Analyze-Paper.bat").read_text(encoding="utf-8")
    command_lines = [
        line.strip().lower()
        for line in launcher.splitlines()
        if line.strip() and not line.strip().lower().startswith("echo")
    ]

    assert any("python 3.10" in line.lower() for line in launcher.splitlines())
    assert any("pip install -r requirements.txt" in line for line in command_lines)
    assert not any("pip install -r requirements-ai.txt" in line for line in command_lines)
    assert "gauntlet_core.cli" in launcher
    assert "requirements-ai.txt" not in launcher


def test_readme_image_links_point_to_existing_files():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    image_paths = re.findall(r"!\[[^\]]*\]\((docs/images/[^)]+)\)", readme)

    assert image_paths
    assert {Path(path).name for path in image_paths} == {
        "gauntlet-summary.png",
        "gauntlet-breakdown.png",
        "gauntlet-workspace.png",
        "gauntlet-source-viewer.png",
        "gauntlet-benchmarks.png",
        "gauntlet-refinement.png",
    }
    assert all((ROOT / path).exists() for path in image_paths)


def test_github_actions_runs_non_ai_test_suite():
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")

    assert "requirements-dev.txt" in workflow
    assert "python -m pytest" in workflow
    assert "requirements-ai.txt" not in workflow


def test_local_workspace_data_is_gitignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".gauntlet/" in gitignore
    assert "gauntlet-reports/" in gitignore


def test_release_checklist_includes_first_run_and_launcher_log_checks():
    checklist = (ROOT / "docs" / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert "launcher log" in checklist.lower()
    assert "Try Sample Paper" in checklist
    assert "System Check" in checklist
    assert "Document Extraction Quality" in checklist
    assert "Reviewer Packet" in checklist
    assert "Open Result Packs" in checklist
    assert "result-pack" in checklist.lower()
    assert "metadata-only" in checklist.lower()


def test_readme_documents_metadata_only_result_packs():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Result Packs" in readme
    assert "The `Result Packs` page" in readme
    assert "metadata-only" in readme
    assert "not the original uploaded paper files" in readme
    assert "result-packs\\landmark-paper-starter.json" in readme
