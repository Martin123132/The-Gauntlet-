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
        "docs/LOCAL_DEVELOPMENT.md",
        "docs/COMMERCIAL_USE.md",
        "docs/OCR_SETUP.md",
        "docs/V0_27_RELEASE_NOTES.md",
        "docs/V0_28_RELEASE_NOTES.md",
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

    assert "D:\\Projects\\The-Gauntlet-" in checklist
    assert "temp/cache/output paths on `D:\\`" in checklist
    assert "launcher log" in checklist.lower()
    assert "Try Sample Paper" in checklist
    assert "Extraction Preview" in checklist
    assert "Paste Text Instead" in checklist
    assert "OCR readiness" in checklist
    assert "V0_28_RELEASE_NOTES.md" in checklist
    assert "System Check" in checklist
    assert "Document Extraction Quality" in checklist
    assert "Reviewer Packet" in checklist
    assert "Open Result Packs" in checklist
    assert "custom manifest" in checklist
    assert "result-pack" in checklist.lower()
    assert "metadata-only" in checklist.lower()


def test_readme_documents_metadata_only_result_packs():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Result Packs" in readme
    assert "The `Result Packs` page" in readme
    assert "Pack Builder" in readme
    assert "Extraction Preview" in readme
    assert "Paste Text Instead" in readme
    assert "OCR_SETUP.md" in readme
    assert "OCR readiness" in readme
    assert "metadata-only" in readme
    assert "not the original uploaded paper files" in readme
    assert "result-packs\\landmark-paper-starter.json" in readme


def test_readme_opens_as_landing_page():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "## What It Does" in readme
    assert "## Quick Start" in readme
    assert "## Screenshots" in readme
    assert "## Trust Model" in readme
    assert "Latest verified release: [`v0.28.0`" in readme
    assert "Download the repo, double-click the Windows launcher" in readme
    assert "The first screen gives users the upload path" in readme
    assert "Optional refinement is clearly separated" in readme


def test_readme_documents_first_user_and_maintainer_storage_guidance():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    local_dev = (ROOT / "docs" / "LOCAL_DEVELOPMENT.md").read_text(encoding="utf-8")

    assert "If launch feels stuck" in readme
    assert ".gauntlet/logs/Start-Gauntlet.log" in readme
    assert "optional OCR readiness" in readme
    assert "D:\\Projects\\The-Gauntlet-" in readme
    assert "archive-only" in readme
    assert "docs/LOCAL_DEVELOPMENT.md" in readme
    assert "Public GitHub ZIP users do not need a special drive layout" in local_dev
    assert "D:\\Temp\\gauntlet-codex" in local_dev
    assert "requirements-ai.txt" in local_dev
    assert "local-first and non-AI" in local_dev


def test_readme_documents_noncommercial_license_boundary():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    commercial_use = (ROOT / "docs" / "COMMERCIAL_USE.md").read_text(encoding="utf-8")
    result_pack_readme = (ROOT / "result-packs" / "README.md").read_text(encoding="utf-8")

    assert "Motion-TimeSpace Non-Commercial License" in readme
    assert "Commercial use requires a separate written commercial license" in readme
    assert "company's COO" in readme
    assert "docs/COMMERCIAL_USE.md" in readme
    assert "does not grant rights to third-party papers" in readme
    assert "The controlling terms are in" in commercial_use
    assert "metadata-only manifests" in commercial_use
    assert "session-only API keys" in commercial_use
    assert "Commercial use of The Gauntlet requires" in result_pack_readme
    assert "does not grant rights to third-party papers" in result_pack_readme


def test_changelog_has_v027_release_section():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    release_notes = (ROOT / "docs" / "V0_27_RELEASE_NOTES.md").read_text(encoding="utf-8")
    release_notes_v028 = (ROOT / "docs" / "V0_28_RELEASE_NOTES.md").read_text(encoding="utf-8")
    zip_qa = (ROOT / "docs" / "V0_27_ZIP_QA.md").read_text(encoding="utf-8")

    assert "## Unreleased\n\nNo changes yet." in changelog
    assert "## v0.28.0 - Public Trust Polish" in changelog
    assert "generated-source-ZIP QA notes" in changelog
    assert "D-drive development/storage guidance" in changelog
    assert "commercial-use guidance" in changelog
    assert "landing-page style overview" in changelog
    assert "## v0.27.0 - Intake, Result Packs, and OCR Readiness" in changelog
    assert "V0.28.0 is a public trust polish release" in release_notes_v028
    assert "Generated GitHub source ZIP smoke" in release_notes_v028
    assert "V0.27.0 is a local-app hardening release" in release_notes
    assert "Generated source ZIP smoke" in release_notes
    assert "OCR processing is not implemented yet" in release_notes
    assert "Generated source ZIP smoke test completed" in zip_qa
    assert "requirements.txt" in zip_qa
