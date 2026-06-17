# The Gauntlet v0.27.0 Release Notes Draft

V0.27.0 is a local-app hardening release for real-paper intake and repeatable
demo workflows. The default checker remains deterministic, local-first, and
non-AI.

## Highlights

- Added `System Check` diagnostics for Python, dependencies, required public
  files, workspace status, launcher logs, optional AI requirements, and optional
  OCR readiness.
- Added document extraction-quality reporting to Summary, Breakdown, Markdown,
  JSON, and HTML reports.
- Added metadata-only Result Packs with a landmark-paper starter manifest.
- Added `Result Packs` UI for running packs from user-supplied local files.
- Added `Pack Builder` for custom metadata-only manifests, import, and export.
- Added pre-analysis `Extraction Preview` with extracted text samples and
  rescue suggestions.
- Added `Paste Text Instead` for scanned/broken PDF fallback.
- Added optional OCR readiness guidance without adding OCR to the base install.

## Privacy Model

- No API key is needed for the normal checker.
- Result-pack manifests contain metadata only, not paper PDFs or copied paper
  text.
- Workspace saves reports, snippets, anchors, notes, and review state, not full
  uploaded paper files.
- OCR is detected only as local readiness. V0.27.0 does not run OCR processing.

## Validation

- Local test suite target: `.venv\Scripts\python.exe -m pytest -q`
- GitHub Actions target: Ubuntu and Windows pytest jobs on `non-ai-app-v1`
- Manual smoke target: Summary, Extraction Preview, Result Packs, System Check,
  Workspace, Benchmarks, and report exports

## Known Limits

- OCR processing is not implemented yet.
- PDF page numbers remain best-effort from extracted text.
- Synthetic benchmarks are calibration cases, not proof of real-world accuracy.
