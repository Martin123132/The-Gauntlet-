# Changelog

## Unreleased

No unreleased changes yet.

## v0.10.0 - Issue-Led Source Review

This release upgrades source anchors into an issue-led review workflow.

### Added

- Added Issue-Led Source Review with prioritized source issues, filters, and a
  Markdown export.

## v0.9.0 - Share Demo Kit

This release adds a public demo pack workflow for posting project updates.

### Added

- Added a Share Demo Kit for X-ready post drafts, social cards, demo summaries,
  and a downloadable synthetic demo bundle.

## v0.8.0 - Batch Bundle HTML Index

This release makes exported batch ZIP bundles easier to open and share offline.

### Added

- Added an offline `index.html` dashboard to batch ZIP bundles.

## v0.7.0 - Demo Batch Mode

This release adds a ready-made demo path for Batch Scan.

### Added

- Added Demo Batch Mode so users can load the synthetic benchmark corpus into
  the Batch page without uploading files.

## v0.6.0 - Batch Sorting and Filters

This release makes Batch Scan easier to use for larger paper sets.

### Added

- Added Batch Scan sorting and filters for verdict, high-risk papers, weak
  evidence, confidence, finding count, and filename.

## v0.5.0 - Reviewer Action Plan

This release adds prioritized repair checklists to help reviewers move from
finding problems to fixing them.

### Added

- Added Reviewer Action Plan for prioritized repair steps in the app,
  Markdown exports, HTML reports, and report bundles.

## v0.4.0 - Batch Scan

This release adds multi-paper scanning for local review workflows.

### Added

- Added Batch Scan for multi-paper upload, verdict tables, CSV export, and
  batch report ZIP bundles.
- Added CLI folder scanning for supported paper files.

## v0.3.0 - Report Sharing and Headless Analysis

This release makes The Gauntlet easier to share, archive, and run outside the
browser UI.

### Added

- Added self-contained HTML report exports for current analyses and saved
  workspace runs.
- Added one-click ZIP report bundles containing JSON, Markdown, HTML, and a
  short privacy/readme note.
- Added a command-line analyzer and `Analyze-Paper.bat` drag-and-drop launcher
  for writing reports without opening Streamlit.

## v0.2.0 - Source Viewer and Saved Workspace

The second public app update makes reports easier to audit and reuse across
multiple paper checks.

### Added

- Added a Source Viewer page with click-through source links and highlighted
  sentence context.
- Added local saved workspace history for completed analyses.
- Added saved-run reload, reviewer notes/status, deletion, export, and
  two-report comparison controls.
- Added report JSON restore support for workspace reloads.
- Added source-map traceability for claims, findings, contradictions, and
  evidence snippets.
- Added structured document loading with best-effort PDF page numbers and
  source anchors in JSON/Markdown exports.

## v0.1.0 - Local Paper Checker

The first public app release of The Gauntlet turns the original Colab and
prototype engines into a local-first paper checker that GitHub users can
download and run on Windows.

### Added

- Local, non-AI paper checking by default with no API key required.
- Windows double-click launcher through `Start-Gauntlet.bat`.
- Upload support for `.pdf`, `.docx`, `.txt`, and `.md` papers.
- Streamlit app pages for Summary, Breakdown, Claims, Contradictions, Evidence,
  Benchmarks, and optional Refinement.
- Rule-based verdicts: `RESOLVES`, `PARTIAL`, `FAILS`, or
  `CREATES_NEW_PARADOXES`.
- Synthetic benchmark gallery for known rule behaviors and regression tests.
- Optional Gemini, OpenAI, and Anthropic refinement using session-only API keys.
- JSON and Markdown report exports.
- Preserved legacy Colab/prototype files under `legacy/colab-originals/`.
- GitHub Actions tests, issue templates, README screenshots, and a release
  checklist for ZIP-download testing.
