# Changelog

## Unreleased

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
