# Changelog

## Unreleased

### Added

- Added public `v0.27.0` generated-source-ZIP QA notes and linked the latest
  verified release from the README.

### Changed

- Clarified first-run install time and optional OCR warning expectations in the
  README and release checklist.

## v0.27.0 - Intake, Result Packs, and OCR Readiness

This release hardens the GitHub ZIP/local-app path for real papers: local
diagnostics, extraction quality, metadata-only result packs, custom pack
building, extraction rescue, paste-text fallback, and optional OCR readiness.

### Added

- Added an in-app `System Check` page with local diagnostics for Python,
  dependencies, required public files, workspace path, launcher log presence,
  and optional AI setup.
- Added diagnostics JSON/Markdown exports for GitHub issues without including
  uploaded paper text, report contents, API keys, or full launcher logs.
- Added document extraction-quality scoring for real-paper uploads, including
  warnings for scanned-looking PDFs, very short extraction, missing source
  anchors, fragmented text, symbol-heavy extraction, and reference-heavy text.
- Added metadata-only Result Packs for repeatable public demos, including a
  landmark-paper starter manifest that stores links and expected filenames but
  no bundled paper PDFs or copied paper text.
- Added CLI support for `--result-pack`, producing JSON, Markdown, and ZIP
  result-pack bundles from user-supplied local paper files.
- Added the `Result Packs` app page for selecting the starter manifest,
  uploading matching local paper copies, running the pack, opening individual
  reports, and exporting JSON, Markdown, or ZIP result-pack bundles.
- Added a `Pack Builder` workflow for creating custom metadata-only manifests,
  importing existing manifest JSON, exporting the active manifest, and validating
  editable manifest rows before a pack run.
- Added upload `Extraction Preview` with pre-analysis quality metrics, extracted
  text samples, rescue suggestions, and a `Paste Text Instead` fallback for
  scanned or broken PDF extraction.
- Added optional OCR readiness detection for Tesseract and Python OCR packages,
  with System Check export data and extraction rescue guidance.

### Changed

- Upload parsing errors now point users toward `System Check` and show
  troubleshooting detail without making raw exceptions the main UI.
- Summary, Breakdown, Markdown, JSON, and HTML reports now include extraction
  quality so users know whether the verdict had usable source text.

## v0.20.0 - Trust Guardrails + Calibration Governance

This release adds governance guardrails to the synthetic calibration layer so
drift is easier to spot and regression risk is visible before release.

### Added

- Added stable internal calibration versioning (`v0.20.0`) for the benchmark corpus.
- Added calibration gate checks (`overall` and `guardrail` thresholds) and
  detailed threshold pass/fail summaries to suite results.
- Added optional local snapshot export to
  `.gauntlet/reports/latest_calibration.json` for reproducible local runs.
- Added failure reasons and category confidence explanations in benchmark and suite
  summaries to make regressions easier to interpret.
- Added new synthetic false-positive counterexamples around scoped prior-work comparisons,
  limitation-first framing, methods-only language, and explicit uncertainty/caution
  language.
- Added Streamlit benchmark dashboard cards for last-run status, threshold checks, and
  gate warnings; category table now includes per-category confidence explanation.

### Changed

- Analyzer trust checks now use explicit pass/fail gating so exploratory local runs can
  stay non-blocking while strict checks in CI can enforce baseline quality.

## v0.19.0 - Calibration Suite + Analyzer Trust Dashboard

This release adds a public calibration layer on top of the synthetic benchmark
gallery so users can see how the deterministic checker behaves across known
theory/paradox-paper patterns.

### Added

- Expanded the synthetic benchmark corpus from 16 to 28 samples, including
  literature-review, definition, future-work, null-result, method-only,
  limitation-only, competing-hypothesis, theorem/proof, and citation-heavy
  guard cases.
- Added positive controls for scoped strong evidence, empirical mechanism
  claims, and clean limitation-aware resolution claims.
- Added `run_calibration_suite()` and `CalibrationSuiteResult` with overall
  pass rate, verdict-match rate, guardrail pass rate, category summaries,
  failing sample IDs, and JSON/Markdown exports.
- Added a Calibration Dashboard to the existing `Benchmarks` page with full
  suite metrics and export buttons.

### Changed

- Tightened non-AI analyzer guardrails so attributed literature/background
  claims, source disclaimers, and citation support are less likely to become
  false-positive resolution claims.
- Updated README benchmark docs to frame calibration as synthetic trust work,
  not proof of real-world accuracy.

## v0.18.0 - First-Run Onboarding + Download QA

This release improves the GitHub ZIP first-run path for new local users.

### Added

- Added a `Start Here` panel on the Summary page when no report is loaded.
- Added a `Try Sample Paper` button that runs the built-in sample and saves the
  result to the local workspace.
- Added launcher diagnostics and a local troubleshooting log under
  `.gauntlet/logs/`.

### Changed

- `Start-Gauntlet.bat` now prints the repo path, virtual environment path,
  Python version, Streamlit URL, and clearer setup failure guidance.
- Updated public docs, release checklist, and screenshots for the first-run
  flow and Reviewer Packet workspace exports.

## v0.17.0 - Reviewer Packet Export

This release adds reviewer-ready exports for sharing The Gauntlet's audit trail
after a local workspace run.

### Added

- Added Reviewer Packet Markdown, HTML, and ZIP exports from saved Workspace
  runs.
- Reviewer packets include the verdict, claim-evidence map, issue review
  register, repair checklist, source snippets, and revision re-check summaries.
- Added reusable `gauntlet_core.reviewer_packet` helpers for packet generation
  without changing the saved report JSON schema.

### Changed

- Workspace saved-run controls now include a dedicated Reviewer Packet export
  section.
- Reviewer Packet exports keep the existing privacy model: snippets, anchors,
  notes, and pasted revision snippets only, not full uploaded paper files or API
  keys.

## v0.16.0 - Issue Review Register

This release adds local issue-level review notes to the Source Reader workflow.

### Added

- Added an Issue Review Register in Source Reader for linked findings, claims,
  evidence items, repair steps, and revision re-checks.
- Added local workspace storage for per-issue review status and reviewer notes.
- Added issue-review summaries on Workspace saved-run cards.

### Changed

- Source Reader issue cards now show saved issue review status when available.
- Workspace storage remains privacy-first and still does not save full uploaded
  paper files or API keys.

## v0.15.0 - Claim-Evidence Map

This release makes evidence traceability easier to audit claim by claim.

### Added

- Added a Claim-Evidence Map on the Evidence page that labels claim coverage as
  `Strong`, `Linked`, `Weak`, or `Missing`.
- Added orphan evidence detection for evidence-like snippets that are not tied
  to a specific claim.
- Added Claim-Evidence Map Markdown export and included the map in standard
  Markdown and HTML reports.
- Added reusable `gauntlet_core.evidence_map` helpers without changing the
  saved report JSON schema.

## v0.14.0 - Source Reader Workspace

This release upgrades source traceability into a reader workspace for real-paper
audit follow-up.

### Added

- Added a Source Reader workspace with source search, section/page filters,
  selected-snippet context, and linked audit panels.
- Added Source Reader Markdown export for selected source references, nearby
  snippets, issue summaries, repair suggestions, and revision re-check notes.
- Added source-reader core helpers for reusable reader views without changing
  saved report JSON.

### Changed

- Retitled the old Source Review nav item to Source Reader while preserving the
  existing `?page=source` route and anchor deep links.
- Repair Workshop and Revision Re-Check cards now link back into Source Reader
  when a source anchor is available.

## v0.13.0 - Revision Re-Check

This release closes the repair loop by letting users test revised snippets
against deterministic rules.

### Added

- Added revision re-checks inside Repair Workshop cards for pasted revised
  sentences or paragraphs.
- Added deterministic re-check results: `Improved`, `Still Weak`, and
  `Introduces New Issue`.
- Added local workspace storage for revision re-check results and a Markdown
  Revision Re-Check Log export.

### Changed

- Workspace cards now summarize saved revision re-check outcomes alongside
  repair progress.

## v0.12.0 - Local Repair Workshop

This release turns findings into a persistent local repair workflow.

### Added

- Added a Repair Workshop page that replaces the old Action Plan label while
  preserving the `?page=action` route.
- Added stable repair steps with statuses, reviewer notes, source references,
  and Markdown export.
- Added local workspace repair progress so saved runs can be reopened and
  resumed without storing the full uploaded paper.

### Changed

- Workspace cards now summarize saved repair progress alongside verdict,
  findings, and reviewer status.

## v0.11.0 - Analyzer Quality Guardrails

This release calibrates the deterministic analyzer to reduce false positives
before adding any new app surface.

### Added

- Expanded the synthetic benchmark corpus from 8 to 16 cases, including
  guardrails for tentative hypotheses, scoped limitations, prior-work
  comparisons, reference-like text, weak equation dumps, and caveated universal
  claims.
- Added benchmark expectations for findings and claim gaps that should stay
  absent, so regressions can catch unwanted false positives.

### Changed

- Made claim extraction and verdict scoring more conservative around tentative,
  background, comparison, and reference-like language.
- Required stronger linked evidence before a paper can receive `RESOLVES`.
- Improved audit/rubric language so reports explain the linked-evidence and
  false-positive guardrail checks.

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
