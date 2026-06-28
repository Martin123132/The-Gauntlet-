# The Gauntlet v0.28.0 Release Notes

V0.28.0 is a public trust polish release. It freezes new feature work for this
milestone and focuses on making the GitHub download experience clearer, safer,
and easier to understand.

## Highlights

- Reworked the README into a landing-page style overview with a clearer product
  summary, quick start, screenshot captions, and trust model.
- Kept the default path local-first and non-AI: no API key is needed for normal
  analysis.
- Clarified first-run dependency installation, launcher logs, stuck-launch
  recovery, and optional OCR warnings.
- Added maintainer-local D-drive storage guidance for release/test work without
  changing the normal public ZIP flow.
- Added commercial-use guidance that points to the non-commercial license and
  separates The Gauntlet's license from third-party paper rights.
- Confirmed existing screenshots cover Summary, Breakdown, Workspace, Source
  Reader, Benchmarks, and Refinement.

## Validation Targets

- `.venv\Scripts\python.exe -m pytest -q`
- `run_calibration_suite(strict=True, persist_snapshot=False)`
- GitHub Actions on Ubuntu and Windows
- Generated GitHub source ZIP smoke after release publication

## Known Limits

- The deterministic verdict is a review aid, not a replacement for expert peer
  review.
- OCR processing is not part of the default install; OCR status is readiness
  guidance only.
- Optional AI refinement remains separate and requires optional dependencies plus
  session-only provider keys.
- Result packs are metadata-only and do not grant rights to third-party papers.
