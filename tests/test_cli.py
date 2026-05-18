from __future__ import annotations

from zipfile import ZipFile

from gauntlet_core.cli import main


def test_cli_writes_default_report_outputs(tmp_path, capsys):
    paper = tmp_path / "paper.txt"
    paper.write_text(
        "The framework resolves the anomaly because the mechanism uses 12 measured observations.",
        encoding="utf-8",
    )
    output_dir = tmp_path / "reports"

    exit_code = main([str(paper), "--out", str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Verdict:" in captured.out
    assert (output_dir / "paper-gauntlet-report.json").exists()
    assert (output_dir / "paper-gauntlet-report.md").exists()
    assert (output_dir / "paper-gauntlet-report.html").exists()
    bundle = output_dir / "paper-gauntlet-report-bundle.zip"
    assert bundle.exists()
    with ZipFile(bundle) as archive:
        assert "README.txt" in archive.namelist()


def test_cli_reports_missing_file_without_traceback(tmp_path, capsys):
    missing = tmp_path / "missing.txt"

    exit_code = main([str(missing), "--out", str(tmp_path / "reports")])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "could not analyze" in captured.err
    assert "Traceback" not in captured.err
