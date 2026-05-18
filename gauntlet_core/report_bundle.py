from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile

from .models import AnalysisReport


def build_report_bundle(report: AnalysisReport) -> bytes:
    """Build a portable ZIP containing every deterministic report format."""
    stem = safe_report_stem(report.source_name)
    json_name = f"{stem}-gauntlet-report.json"
    markdown_name = f"{stem}-gauntlet-report.md"
    html_name = f"{stem}-gauntlet-report.html"
    readme_name = "README.txt"

    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr(json_name, report.to_json())
        bundle.writestr(markdown_name, report.to_markdown())
        bundle.writestr(html_name, report.to_html())
        bundle.writestr(readme_name, bundle_readme(report, [json_name, markdown_name, html_name]))
    return buffer.getvalue()


def bundle_readme(report: AnalysisReport, files: list[str]) -> str:
    file_lines = "\n".join(f"- {name}" for name in files)
    return "\n".join(
        [
            "The Gauntlet Report Bundle",
            "",
            f"Source: {report.source_name}",
            f"Verdict: {report.verdict}",
            f"Confidence: {report.confidence:.0%}",
            f"Evidence quality: {report.evidence.score:.2f}/1.00",
            f"Generated: {report.created_at}",
            "",
            "Included files:",
            file_lines,
            "",
            "JSON is best for automation, Markdown is best for notes or GitHub issues, and HTML is best for sharing a readable offline report.",
            "",
            "Privacy note: this bundle contains the deterministic report plus source snippets and anchors already present in the report. It does not include the full uploaded paper file or any API keys.",
            "",
        ]
    )


def safe_report_stem(source_name: str) -> str:
    raw_stem = Path(source_name or "paper").stem or "paper"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_stem).strip(".-_")
    return safe[:80] or "paper"
