from __future__ import annotations

from zipfile import ZipFile

from gauntlet_core.cli import main, supported_files_in_directory


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


def test_cli_scans_directory_and_writes_batch_outputs(tmp_path, capsys):
    papers = tmp_path / "papers"
    papers.mkdir()
    (papers / "first.txt").write_text(
        "The framework resolves the anomaly because the mechanism uses 12 measured observations.",
        encoding="utf-8",
    )
    (papers / "second.md").write_text(
        "The model explains the contradiction because the equation x = 1 is measured in 20 trials.",
        encoding="utf-8",
    )
    (papers / "ignore.csv").write_text("not supported", encoding="utf-8")
    output_dir = tmp_path / "reports"

    exit_code = main([str(papers), "--out", str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Batch scan complete: 2 analyzed, 0 failed" in captured.out
    assert (output_dir / "gauntlet-batch-summary.csv").exists()
    assert (output_dir / "gauntlet-batch-report-bundle.zip").exists()
    assert [path.name for path in supported_files_in_directory(papers)] == ["first.txt", "second.md"]
