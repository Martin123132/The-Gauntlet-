from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest

from gauntlet_core import analyze_paper_text
from gauntlet_core.result_packs import (
    ResultPackManifest,
    build_result_pack_manifest,
    build_result_pack_bundle,
    load_result_pack_manifest,
    result_pack_to_markdown,
    run_result_pack_file_bytes,
    run_result_pack,
)


ROOT = Path(__file__).resolve().parents[1]


def test_starter_manifest_loads_and_is_metadata_only():
    manifest = load_result_pack_manifest(ROOT / "result-packs" / "landmark-paper-starter.json")

    assert manifest.id == "landmark-paper-starter"
    assert len(manifest.entries) == 10
    assert all(entry.expected_filename.endswith(".pdf") for entry in manifest.entries)
    assert "does not include or redistribute paper PDFs" in manifest.description
    assert "uploaded documents" in manifest.privacy_note


def test_build_result_pack_manifest_from_editable_rows():
    manifest = build_result_pack_manifest(
        "My Pack",
        "Custom metadata-only pack.",
        [
            {
                "title": "First Paper",
                "expected_filename": "first-paper.pdf",
                "authors": "A. Example",
                "year": "2026",
                "category": "custom",
                "source_url": "https://example.com/first",
                "license_note": "Verify source terms.",
            },
            {
                "title": "First Paper",
                "expected_filename": "first-paper-again.md",
            },
            {"title": "", "expected_filename": ""},
        ],
    )

    assert manifest.id == "my-pack"
    assert len(manifest.entries) == 2
    assert manifest.entries[0].id == "first-paper-first-paper"
    assert manifest.entries[1].id == "first-paper-first-paper-again"
    assert manifest.entries[0].source_url == "https://example.com/first"


def test_build_result_pack_manifest_rejects_incomplete_rows():
    with pytest.raises(ValueError, match="missing a title"):
        build_result_pack_manifest(
            "Bad Pack",
            "Bad",
            [{"title": "", "expected_filename": "paper.pdf"}],
        )

    with pytest.raises(ValueError, match="missing expected_filename"):
        build_result_pack_manifest(
            "Bad Pack",
            "Bad",
            [{"title": "Paper", "expected_filename": ""}],
        )


def test_result_pack_run_handles_success_and_missing_files(tmp_path):
    papers = tmp_path / "papers"
    papers.mkdir()
    (papers / "present.txt").write_text(
        "The framework resolves the anomaly because the mechanism uses 12 measured observations.",
        encoding="utf-8",
    )
    manifest = ResultPackManifest.from_dict(
        {
            "id": "demo-pack",
            "title": "Demo Pack",
            "description": "Local metadata-only demo.",
            "entries": [
                {
                    "id": "present",
                    "title": "Present Paper",
                    "expected_filename": "present.txt",
                    "source_url": "https://example.com/present",
                },
                {
                    "id": "missing",
                    "title": "Missing Paper",
                    "expected_filename": "missing.md",
                },
            ],
        }
    )

    def analyzer(path: Path):
        return analyze_paper_text(path.read_text(encoding="utf-8"), source_name=path.name)

    run = run_result_pack(manifest, papers, analyzer=analyzer)

    assert run.analyzed_count == 1
    assert run.failed_count == 1
    assert run.items[0].status == "analyzed"
    assert run.items[1].status == "failed"
    assert "Missing expected file" in run.items[1].error
    assert run.to_summary_dict()["results"][0]["entry_id"] == "present"


def test_result_pack_file_bytes_matches_upload_names_and_saves_reports():
    manifest = ResultPackManifest.from_dict(
        {
            "id": "upload-pack",
            "title": "Upload Pack",
            "description": "In-memory upload demo.",
            "entries": [
                {"id": "present", "title": "Present", "expected_filename": "present.txt"},
                {"id": "missing", "title": "Missing", "expected_filename": "missing.md"},
            ],
        }
    )
    saved = []

    run = run_result_pack_file_bytes(
        manifest,
        {"present.txt": b"The framework resolves the anomaly because 12 measured observations support the mechanism."},
        save_report=saved.append,
    )

    assert run.papers_dir == "uploaded files"
    assert run.analyzed_count == 1
    assert run.failed_count == 1
    assert saved[0].source_name == "present.txt"
    assert run.items[0].report is saved[0]
    assert "Missing expected file" in run.items[1].error


def test_result_pack_exports_markdown_and_bundle_without_original_files(tmp_path):
    papers = tmp_path / "papers"
    papers.mkdir()
    paper = papers / "paper.txt"
    paper.write_text(
        "The theory resolves the paradox because the mechanism is measured across 20 observations.",
        encoding="utf-8",
    )
    manifest = ResultPackManifest.from_dict(
        {
            "id": "export-pack",
            "title": "Export Pack",
            "description": "Export demo.",
            "entries": [{"id": "paper", "title": "Paper", "expected_filename": "paper.txt"}],
        }
    )

    run = run_result_pack(
        manifest,
        papers,
        analyzer=lambda path: analyze_paper_text(path.read_text(encoding="utf-8"), source_name=path.name),
    )
    markdown = result_pack_to_markdown(run)

    assert "# Export Pack" in markdown
    assert "Privacy" in markdown
    assert "Paper" in markdown

    bundle_path = tmp_path / "result-pack.zip"
    bundle_path.write_bytes(build_result_pack_bundle(run))
    with ZipFile(bundle_path) as archive:
        names = set(archive.namelist())
        assert "index.html" in names
        assert "result-pack-summary.json" in names
        assert "result-pack-summary.md" in names
        assert "result-pack-manifest.json" in names
        assert "gauntlet-batch-report-bundle.zip" in names
        assert "batch/index.html" in names
        assert "batch/reports/paper/paper-gauntlet-report.html" in names
        assert "paper.txt" not in names
        assert "original uploaded documents" in archive.read("result-pack-manifest.json").decode("utf-8")


def test_result_pack_manifest_rejects_paths_and_unsupported_files():
    with pytest.raises(ValueError, match="filename, not a path"):
        ResultPackManifest.from_dict(
            {
                "id": "bad",
                "title": "Bad",
                "description": "Bad",
                "entries": [{"id": "paper", "title": "Paper", "expected_filename": "folder/paper.txt"}],
            }
        )

    with pytest.raises(ValueError, match="supported file type"):
        ResultPackManifest.from_dict(
            {
                "id": "bad",
                "title": "Bad",
                "description": "Bad",
                "entries": [{"id": "paper", "title": "Paper", "expected_filename": "paper.csv"}],
            }
        )
