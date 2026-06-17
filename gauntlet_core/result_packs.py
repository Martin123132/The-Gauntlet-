from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile

from .analysis import analyze_loaded_document
from .batch import (
    BatchScanItem,
    batch_items_to_csv,
    batch_items_to_html,
    batch_items_to_json,
    batch_items_to_markdown,
    build_batch_report_bundle,
    summarize_report,
)
from .document_loader import SUPPORTED_EXTENSIONS, load_document_from_bytes, load_document_from_path
from .models import AnalysisReport


MANIFEST_SCHEMA_VERSION = "v1"
DEFAULT_PRIVACY_NOTE = (
    "Result packs in this repo store metadata and links only. Users supply their "
    "own local paper files; generated bundles contain Gauntlet reports, source "
    "snippets, anchors, and summaries, but not the original uploaded documents."
)


@dataclass(frozen=True)
class ResultPackEntry:
    id: str
    title: str
    expected_filename: str
    authors: str = ""
    year: str = ""
    category: str = "landmark"
    source_url: str = ""
    license_note: str = ""
    why_include: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ResultPackEntry":
        return cls(
            id=str(data.get("id", "")).strip(),
            title=str(data.get("title", "")).strip(),
            authors=str(data.get("authors", "")).strip(),
            year=str(data.get("year", "")).strip(),
            category=str(data.get("category", "landmark")).strip() or "landmark",
            source_url=str(data.get("source_url", "")).strip(),
            expected_filename=str(data.get("expected_filename", "")).strip(),
            license_note=str(data.get("license_note", "")).strip(),
            why_include=str(data.get("why_include", "")).strip(),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "category": self.category,
            "source_url": self.source_url,
            "expected_filename": self.expected_filename,
            "license_note": self.license_note,
            "why_include": self.why_include,
        }


@dataclass(frozen=True)
class ResultPackManifest:
    id: str
    title: str
    description: str
    entries: tuple[ResultPackEntry, ...]
    schema_version: str = MANIFEST_SCHEMA_VERSION
    privacy_note: str = DEFAULT_PRIVACY_NOTE

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ResultPackManifest":
        entries_data = data.get("entries", [])
        if not isinstance(entries_data, list):
            raise ValueError("Result pack manifest entries must be a list")
        entries = tuple(ResultPackEntry.from_dict(entry) for entry in entries_data if isinstance(entry, dict))
        manifest = cls(
            schema_version=str(data.get("schema_version", MANIFEST_SCHEMA_VERSION)).strip() or MANIFEST_SCHEMA_VERSION,
            id=str(data.get("id", "")).strip(),
            title=str(data.get("title", "")).strip(),
            description=str(data.get("description", "")).strip(),
            privacy_note=str(data.get("privacy_note", DEFAULT_PRIVACY_NOTE)).strip() or DEFAULT_PRIVACY_NOTE,
            entries=entries,
        )
        validate_manifest(manifest)
        return manifest

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "privacy_note": self.privacy_note,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def build_result_pack_manifest(
    title: str,
    description: str,
    rows: list[dict[str, object]],
    pack_id: str = "",
    privacy_note: str = DEFAULT_PRIVACY_NOTE,
) -> ResultPackManifest:
    """Build and validate a manifest from editable UI rows."""
    clean_title = title.strip()
    clean_pack_id = slugify(pack_id or clean_title or "custom-result-pack")
    entries: list[dict[str, object]] = []
    used_ids: set[str] = set()
    for row in rows:
        entry = result_pack_entry_from_row(row, used_ids)
        if entry:
            entries.append(entry)
    return ResultPackManifest.from_dict(
        {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "id": clean_pack_id,
            "title": clean_title,
            "description": description.strip(),
            "privacy_note": privacy_note.strip() or DEFAULT_PRIVACY_NOTE,
            "entries": entries,
        }
    )


def result_pack_entry_from_row(row: dict[str, object], used_ids: set[str]) -> dict[str, object] | None:
    title = str(row.get("title", "") or row.get("Title", "")).strip()
    expected_filename = str(row.get("expected_filename", "") or row.get("Expected filename", "")).strip()
    if not title and not expected_filename:
        return None
    if not title:
        raise ValueError(f"Entry for {expected_filename or 'untitled paper'} is missing a title")
    if not expected_filename:
        raise ValueError(f"Entry for {title} is missing expected_filename")

    raw_id = str(row.get("id", "") or row.get("ID", "")).strip()
    entry_id = unique_slug(raw_id or f"{title}-{Path(expected_filename).stem}", used_ids)
    return {
        "id": entry_id,
        "title": title,
        "expected_filename": expected_filename,
        "authors": str(row.get("authors", "") or row.get("Authors", "")).strip(),
        "year": str(row.get("year", "") or row.get("Year", "")).strip(),
        "category": str(row.get("category", "") or row.get("Category", "") or "custom").strip(),
        "source_url": str(row.get("source_url", "") or row.get("Source link", "")).strip(),
        "license_note": str(row.get("license_note", "") or row.get("License note", "")).strip(),
        "why_include": str(row.get("why_include", "") or row.get("Why include", "")).strip(),
    }


def unique_slug(value: str, used_ids: set[str]) -> str:
    base = slugify(value or "entry")
    candidate = base
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "entry"


@dataclass(frozen=True)
class ResultPackRun:
    manifest: ResultPackManifest
    papers_dir: str
    items: tuple[BatchScanItem, ...] = field(default_factory=tuple)

    @property
    def analyzed_count(self) -> int:
        return sum(1 for item in self.items if item.status == "analyzed")

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.items if item.status != "analyzed")

    def to_summary_dict(self) -> dict[str, object]:
        return {
            "manifest": {
                "id": self.manifest.id,
                "title": self.manifest.title,
                "schema_version": self.manifest.schema_version,
                "entry_count": len(self.manifest.entries),
                "privacy_note": self.manifest.privacy_note,
            },
            "papers_dir": self.papers_dir,
            "analyzed": self.analyzed_count,
            "failed_or_missing": self.failed_count,
            "results": [result_pack_item_to_dict(entry, item) for entry, item in zip(self.manifest.entries, self.items)],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_summary_dict(), indent=2)


def load_result_pack_manifest(path: str | Path) -> ResultPackManifest:
    manifest_path = Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Result pack manifest must be a JSON object")
    return ResultPackManifest.from_dict(data)


def validate_manifest(manifest: ResultPackManifest) -> None:
    if not manifest.id:
        raise ValueError("Result pack manifest is missing an id")
    if not manifest.title:
        raise ValueError("Result pack manifest is missing a title")
    if not manifest.entries:
        raise ValueError("Result pack manifest must include at least one entry")

    seen_ids: set[str] = set()
    for entry in manifest.entries:
        if not entry.id:
            raise ValueError("Every result pack entry needs an id")
        if entry.id in seen_ids:
            raise ValueError(f"Duplicate result pack entry id: {entry.id}")
        seen_ids.add(entry.id)
        if not entry.title:
            raise ValueError(f"Result pack entry {entry.id} is missing a title")
        if not entry.expected_filename:
            raise ValueError(f"Result pack entry {entry.id} is missing expected_filename")
        if Path(entry.expected_filename).name != entry.expected_filename:
            raise ValueError(f"Result pack entry {entry.id} expected_filename must be a filename, not a path")
        if Path(entry.expected_filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValueError(f"Result pack entry {entry.id} must use a supported file type: {supported}")


def run_result_pack(
    manifest: ResultPackManifest,
    papers_dir: str | Path,
    analyzer=None,
    save_report=None,
) -> ResultPackRun:
    """Analyze user-supplied local files for a metadata-only result pack."""
    root = Path(papers_dir)
    analyze = analyzer or analyze_result_pack_path
    items: list[BatchScanItem] = []
    for entry in manifest.entries:
        paper_path = root / entry.expected_filename
        if not paper_path.exists():
            items.append(result_pack_failure(entry, f"Missing expected file: {entry.expected_filename}"))
            continue
        if not paper_path.is_file():
            items.append(result_pack_failure(entry, f"Expected a file, found something else: {entry.expected_filename}"))
            continue
        try:
            report: AnalysisReport = analyze(paper_path)
            if save_report:
                save_report(report)
            items.append(summarize_report(report))
        except Exception as exc:
            items.append(result_pack_failure(entry, str(exc)))
    return ResultPackRun(manifest=manifest, papers_dir=str(root), items=tuple(items))


def run_result_pack_file_bytes(
    manifest: ResultPackManifest,
    files: dict[str, bytes],
    save_report=None,
    papers_dir: str = "uploaded files",
) -> ResultPackRun:
    """Analyze in-memory user-supplied files matched by manifest filename."""
    files_by_name = {Path(filename).name: content for filename, content in files.items()}
    items: list[BatchScanItem] = []
    for entry in manifest.entries:
        content = files_by_name.get(entry.expected_filename)
        if content is None:
            items.append(result_pack_failure(entry, f"Missing expected file: {entry.expected_filename}"))
            continue
        try:
            document = load_document_from_bytes(entry.expected_filename, content)
            if not document.text.strip():
                raise ValueError("No readable text was found in that file")
            report = analyze_loaded_document(document)
            if save_report:
                save_report(report)
            items.append(summarize_report(report))
        except Exception as exc:
            items.append(result_pack_failure(entry, str(exc)))
    return ResultPackRun(manifest=manifest, papers_dir=papers_dir, items=tuple(items))


def analyze_result_pack_path(path: Path) -> AnalysisReport:
    document = load_document_from_path(path)
    if not document.text.strip():
        raise ValueError("No readable text was found in that file")
    return analyze_loaded_document(document)


def result_pack_failure(entry: ResultPackEntry, error: str) -> BatchScanItem:
    return BatchScanItem(source_name=entry.expected_filename, status="failed", error=error)


def result_pack_item_to_dict(entry: ResultPackEntry, item: BatchScanItem) -> dict[str, object]:
    summary = item.to_summary_dict()
    summary.update(
        {
            "entry_id": entry.id,
            "title": entry.title,
            "authors": entry.authors,
            "year": entry.year,
            "category": entry.category,
            "source_url": entry.source_url,
            "license_note": entry.license_note,
            "why_include": entry.why_include,
            "expected_filename": entry.expected_filename,
        }
    )
    return summary


def result_pack_to_markdown(run: ResultPackRun) -> str:
    lines = [
        f"# {run.manifest.title}",
        "",
        run.manifest.description,
        "",
        "## Summary",
        "",
        f"- Manifest: `{run.manifest.id}`",
        f"- Schema version: `{run.manifest.schema_version}`",
        f"- Expected papers: **{len(run.manifest.entries)}**",
        f"- Analyzed: **{run.analyzed_count}**",
        f"- Failed or missing: **{run.failed_count}**",
        f"- Papers folder: `{run.papers_dir}`",
        "",
        "## Privacy",
        "",
        run.manifest.privacy_note,
        "",
        "## Results",
        "",
        "| Paper | Status | Verdict | Evidence | Findings | Notes |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for entry, item in zip(run.manifest.entries, run.items):
        notes = item.error or "; ".join(item.top_findings) or entry.why_include or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_markdown_cell(entry.title),
                    item.status,
                    item.verdict or "-",
                    f"{item.evidence_score:.2f}" if item.status == "analyzed" else "-",
                    str(item.finding_count) if item.status == "analyzed" else "-",
                    escape_markdown_cell(notes),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Manifest Entries", ""])
    for entry in run.manifest.entries:
        lines.extend(
            [
                f"### {entry.title}",
                "",
                f"- Entry ID: `{entry.id}`",
                f"- Expected filename: `{entry.expected_filename}`",
                f"- Authors: {entry.authors or '-'}",
                f"- Year: {entry.year or '-'}",
                f"- Category: {entry.category}",
                f"- Source link: {entry.source_url or '-'}",
                f"- License note: {entry.license_note or 'User must verify redistribution rights before sharing paper files.'}",
                f"- Why include: {entry.why_include or '-'}",
                "",
            ]
        )
    return "\n".join(lines)


def result_pack_to_html(run: ResultPackRun) -> str:
    rows = "\n".join(render_result_pack_row(entry, item) for entry, item in zip(run.manifest.entries, run.items))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{escape(run.manifest.title)}</title>",
            "<style>",
            RESULT_PACK_CSS,
            "</style>",
            "</head>",
            "<body>",
            '<main class="shell">',
            '<section class="hero">',
            "<div>",
            '<p class="eyebrow">The Gauntlet Results Pack</p>',
            f"<h1>{escape(run.manifest.title)}</h1>",
            f"<p>{escape(run.manifest.description)}</p>",
            "</div>",
            '<div class="metric-card">',
            "<span>Analyzed</span>",
            f"<strong>{run.analyzed_count}/{len(run.manifest.entries)}</strong>",
            "<small>user-supplied local files</small>",
            "</div>",
            "</section>",
            '<section class="panel privacy">',
            "<h2>Privacy</h2>",
            f"<p>{escape(run.manifest.privacy_note)}</p>",
            "</section>",
            '<section class="panel compact">',
            "<h2>Detailed Reports</h2>",
            '<p>Open the expanded <a href="batch/index.html">batch report index</a> for per-paper HTML reports, JSON, Markdown, and reviewer action plans.</p>',
            "</section>",
            '<section class="panel">',
            "<h2>Pack Results</h2>",
            '<div class="table-wrap">',
            "<table>",
            "<thead><tr><th>Paper</th><th>Status</th><th>Verdict</th><th>Evidence</th><th>Findings</th><th>Source</th><th>Notes</th></tr></thead>",
            f"<tbody>{rows}</tbody>",
            "</table>",
            "</div>",
            "</section>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def render_result_pack_row(entry: ResultPackEntry, item: BatchScanItem) -> str:
    source = "-"
    if entry.source_url:
        source = f'<a href="{escape(entry.source_url, quote=True)}">Source link</a>'
    notes = item.error or "; ".join(item.top_findings) or entry.why_include or "-"
    return f"""
<tr>
  <td><strong>{escape(entry.title)}</strong><small>{escape(entry.authors)} {escape(entry.year)}</small></td>
  <td>{escape(item.status)}</td>
  <td>{escape(item.verdict or "-")}</td>
  <td>{escape(f"{item.evidence_score:.2f}" if item.status == "analyzed" else "-")}</td>
  <td>{escape(str(item.finding_count) if item.status == "analyzed" else "-")}</td>
  <td>{source}</td>
  <td>{escape(notes)}</td>
</tr>
"""


def build_result_pack_bundle(run: ResultPackRun) -> bytes:
    buffer = BytesIO()
    batch_bundle_bytes = build_batch_report_bundle(list(run.items))
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr("index.html", result_pack_to_html(run))
        bundle.writestr("result-pack-summary.json", run.to_json())
        bundle.writestr("result-pack-summary.md", result_pack_to_markdown(run))
        bundle.writestr("result-pack-manifest.json", run.manifest.to_json())
        bundle.writestr("batch-summary.csv", batch_items_to_csv(list(run.items)))
        bundle.writestr("batch-summary.json", batch_items_to_json(list(run.items)))
        bundle.writestr("batch-summary.md", batch_items_to_markdown(list(run.items)))
        bundle.writestr("README.txt", result_pack_readme(run))
        bundle.writestr("gauntlet-batch-report-bundle.zip", batch_bundle_bytes)
        with ZipFile(BytesIO(batch_bundle_bytes)) as batch_bundle:
            for name in batch_bundle.namelist():
                bundle.writestr(f"batch/{name}", batch_bundle.read(name))
    return buffer.getvalue()


def result_pack_readme(run: ResultPackRun) -> str:
    return "\n".join(
        [
            "The Gauntlet Results Pack",
            "",
            f"Manifest: {run.manifest.title} ({run.manifest.id})",
            f"Papers expected: {len(run.manifest.entries)}",
            f"Analyzed: {run.analyzed_count}",
            f"Failed or missing: {run.failed_count}",
            "",
            "Included files:",
            "- index.html",
            "- result-pack-summary.json",
            "- result-pack-summary.md",
            "- result-pack-manifest.json",
            "- batch-summary.csv/json/md",
            "- gauntlet-batch-report-bundle.zip",
            "- batch/index.html",
            "- batch/reports/<paper>/<paper>-gauntlet-report.html",
            "",
            "Privacy note: this bundle includes Gauntlet reports, source snippets, anchors, and summaries. It does not include the original full paper files or any API keys.",
            "",
        ]
    )


def escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


RESULT_PACK_CSS = """
:root {
  color-scheme: light;
  --ink: #18231f;
  --muted: #60706a;
  --line: #dce5df;
  --paper: #f6f8f5;
  --panel: #ffffff;
  --green: #1f6f4a;
  --red: #9b2f2f;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  color: var(--ink);
  background: var(--paper);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.shell {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 40px 0;
}
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 20px;
  align-items: stretch;
  padding: 28px;
  border: 1px solid var(--line);
  background: var(--panel);
}
.eyebrow {
  margin: 0 0 10px;
  color: var(--green);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}
h1, h2, p { margin-top: 0; }
h1 { margin-bottom: 12px; font-size: clamp(2rem, 4vw, 3.6rem); line-height: 1; }
p { color: var(--muted); line-height: 1.6; }
.panel, .metric-card {
  border: 1px solid var(--line);
  background: var(--panel);
}
.panel {
  margin-top: 16px;
  padding: 24px;
}
.metric-card {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 20px;
}
.metric-card span {
  color: var(--muted);
  font-size: 0.76rem;
  font-weight: 800;
  text-transform: uppercase;
}
.metric-card strong {
  margin: 8px 0;
  font-size: 2.4rem;
}
.metric-card small, td small {
  color: var(--muted);
}
td small {
  display: block;
  margin-top: 4px;
}
.table-wrap { overflow-x: auto; }
table {
  width: 100%;
  min-width: 920px;
  border-collapse: collapse;
}
th, td {
  padding: 12px 10px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}
th {
  color: var(--muted);
  font-size: 0.78rem;
  text-transform: uppercase;
}
a {
  color: var(--green);
  font-weight: 800;
}
@media (max-width: 780px) {
  .hero { grid-template-columns: 1fr; }
}
"""
