from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .analysis import analyze_loaded_document
from .batch import BatchScanItem, build_batch_report_bundle, batch_items_to_csv, summarize_report
from .document_loader import SUPPORTED_EXTENSIONS, load_document_from_path
from .models import AnalysisReport
from .report_bundle import safe_report_stem
from .workspace import save_analysis_run


OutputFormat = str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m gauntlet_core.cli",
        description="Run The Gauntlet local checker from the command line without opening the Streamlit UI.",
    )
    parser.add_argument("paper", type=Path, help="Path to a .pdf, .docx, .txt, or .md paper, or a folder of papers.")
    parser.add_argument(
        "--out",
        "-o",
        type=Path,
        default=Path("gauntlet-reports"),
        help="Directory where report files should be written. Defaults to gauntlet-reports/.",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=("all", "json", "markdown", "html", "bundle"),
        default="all",
        help="Report format to write. 'all' writes JSON, Markdown, HTML, and ZIP bundle.",
    )
    parser.add_argument(
        "--save-workspace",
        action="store_true",
        help="Also save the report metadata to the local .gauntlet workspace.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="When the input is a folder, scan supported files in subfolders too.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.paper.is_dir():
            items = analyze_paper_directory(args.paper, recursive=args.recursive, save_workspace=args.save_workspace)
            written_files = write_batch_outputs(items, args.out)
            print_batch_summary(items, written_files)
            return 0
        report = analyze_paper_path(args.paper)
        written_files = write_report_outputs(report, args.out, args.format)
        if args.save_workspace:
            save_analysis_run(report, run_kind="cli")
    except Exception as exc:
        print(f"The Gauntlet could not analyze that paper: {exc}", file=sys.stderr)
        return 1

    print(f"Verdict: {report.verdict}")
    print(f"Confidence: {report.confidence:.0%}")
    print(f"Evidence quality: {report.evidence.score:.2f}/1.00")
    print("Reports written:")
    for path in written_files:
        print(f"- {path}")
    return 0


def analyze_paper_path(path: Path) -> AnalysisReport:
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")
    if not path.is_file():
        raise ValueError(f"{path} is not a file")
    document = load_document_from_path(path)
    if not document.text.strip():
        raise ValueError("No readable text was found in that file")
    return analyze_loaded_document(document)


def analyze_paper_directory(path: Path, recursive: bool = False, save_workspace: bool = False) -> list[BatchScanItem]:
    files = supported_files_in_directory(path, recursive=recursive)
    if not files:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"No supported papers were found in {path}. Supported types: {supported}")

    items: list[BatchScanItem] = []
    for paper_path in files:
        try:
            report = analyze_paper_path(paper_path)
            if save_workspace:
                save_analysis_run(report, run_kind="cli-batch")
            items.append(summarize_report(report))
        except Exception as exc:
            items.append(BatchScanItem(source_name=paper_path.name, status="failed", error=str(exc)))
    return items


def supported_files_in_directory(path: Path, recursive: bool = False) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    files = [
        candidate
        for candidate in path.glob(pattern)
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(files, key=lambda item: str(item).lower())


def write_report_outputs(report: AnalysisReport, output_dir: Path, output_format: OutputFormat = "all") -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = safe_report_stem(report.source_name)
    outputs: list[tuple[str, bytes | str]] = []

    if output_format in {"all", "json"}:
        outputs.append((f"{stem}-gauntlet-report.json", report.to_json()))
    if output_format in {"all", "markdown"}:
        outputs.append((f"{stem}-gauntlet-report.md", report.to_markdown()))
    if output_format in {"all", "html"}:
        outputs.append((f"{stem}-gauntlet-report.html", report.to_html()))
    if output_format in {"all", "bundle"}:
        outputs.append((f"{stem}-gauntlet-report-bundle.zip", report.to_bundle_bytes()))

    written: list[Path] = []
    for filename, content in outputs:
        path = output_dir / filename
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def write_batch_outputs(items: list[BatchScanItem], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[tuple[str, bytes | str]] = [
        ("gauntlet-batch-summary.csv", batch_items_to_csv(items)),
        ("gauntlet-batch-report-bundle.zip", build_batch_report_bundle(items)),
    ]
    written: list[Path] = []
    for filename, content in outputs:
        path = output_dir / filename
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def print_batch_summary(items: list[BatchScanItem], written_files: list[Path]) -> None:
    analyzed = sum(1 for item in items if item.status == "analyzed")
    failed = sum(1 for item in items if item.status == "failed")
    print(f"Batch scan complete: {analyzed} analyzed, {failed} failed")
    print("Reports written:")
    for path in written_files:
        print(f"- {path}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
