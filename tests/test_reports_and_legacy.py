import json
from pathlib import Path
from zipfile import ZipFile

from gauntlet_core import analyze_paper_text


def test_report_exports_include_core_fields(tmp_path):
    report = analyze_paper_text(
        "The framework explains the anomaly through a mechanism with equation x = 1.",
        source_name="paper.txt",
    )

    data = json.loads(report.to_json())
    markdown = report.to_markdown()
    html = report.to_html()
    bundle = report.to_bundle_bytes()

    assert data["source_name"] == "paper.txt"
    assert data["verdict"] in {"RESOLVES", "PARTIAL", "FAILS", "CREATES_NEW_PARADOXES"}
    assert data["source_spans"]
    assert data["claims"][0]["source_span"]
    assert "The Gauntlet Report: paper.txt" in markdown
    assert "Claim-Evidence Map" in markdown
    assert "Evidence Profile" in markdown
    assert "Source Trace" in markdown
    assert "Reviewer Action Plan" in markdown
    assert "<!doctype html>" in html
    assert "The Gauntlet Report: paper.txt" in html
    assert "Confidence" in html
    assert "Claim-Evidence Map" in html
    assert "Evidence Profile" in html
    assert "Source Highlights" in html
    assert "Reviewer Action Plan" in html
    assert "deterministic local rules" in html

    bundle_path = tmp_path / "report.zip"
    bundle_path.write_bytes(bundle)
    with ZipFile(bundle_path) as archive:
        names = set(archive.namelist())
        assert "paper-gauntlet-report.json" in names
        assert "paper-gauntlet-report.md" in names
        assert "paper-gauntlet-report.html" in names
        assert "paper-reviewer-action-plan.md" in names
        assert "README.txt" in names
        readme = archive.read("README.txt").decode("utf-8")
        assert "The Gauntlet Report Bundle" in readme
        assert "does not include the full uploaded paper file" in readme


def test_html_report_escapes_source_text():
    report = analyze_paper_text(
        "The framework resolves <script>alert('x')</script> because the mechanism uses 12 measured observations.",
        source_name="unsafe.html",
    )

    html = report.to_html()

    assert "&lt;script&gt;" in html
    assert "<script>alert" not in html


def test_legacy_colab_files_are_preserved():
    root = Path(__file__).resolve().parents[1]
    legacy = root / "legacy" / "colab-originals"

    assert legacy.exists()
    assert (legacy / "Pure Paradox Resolution Engine").exists()
    assert (legacy / "universal paradox and contradiction finder").exists()
    assert (legacy / "README-original.md").exists()
