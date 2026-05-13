import json
from pathlib import Path

from gauntlet_core import analyze_paper_text


def test_report_exports_include_core_fields():
    report = analyze_paper_text(
        "The framework explains the anomaly through a mechanism with equation x = 1.",
        source_name="paper.txt",
    )

    data = json.loads(report.to_json())
    markdown = report.to_markdown()

    assert data["source_name"] == "paper.txt"
    assert data["verdict"] in {"RESOLVES", "PARTIAL", "FAILS", "CREATES_NEW_PARADOXES"}
    assert "The Gauntlet Report: paper.txt" in markdown
    assert "Evidence Profile" in markdown


def test_legacy_colab_files_are_preserved():
    root = Path(__file__).resolve().parents[1]
    legacy = root / "legacy" / "colab-originals"

    assert legacy.exists()
    assert (legacy / "Pure Paradox Resolution Engine").exists()
    assert (legacy / "universal paradox and contradiction finder").exists()
    assert (legacy / "README-original.md").exists()
