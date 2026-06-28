# The Gauntlet Roadmap

V0.28 is the finished public local-app milestone. The next phase should protect
trust, reduce support friction, and gather real user feedback before adding
major new surfaces.

## Current Mode

- Keep the public default local-first and non-AI.
- Keep optional Gemini/OpenAI/Anthropic refinement separate from the normal
  checker and `requirements.txt`.
- Treat the README, screenshots, release notes, launcher, and generated ZIP path
  as product surfaces.
- Prefer maintenance, calibration, documentation, and small quality fixes over
  new app pages.
- Continue to keep result packs metadata-only and separate from third-party
  paper rights.

## Maintenance Gates

Before any future release:

1. Run full local tests.
2. Run strict calibration.
3. Run the GitHub Actions Ubuntu and Windows matrix.
4. Run a generated source ZIP smoke test after publishing.
5. Confirm `Start-Gauntlet.bat` installs only `requirements.txt`.
6. Confirm README, license, commercial-use docs, result-pack docs, and release
   notes agree.
7. Confirm no full uploaded paper files, API keys, or commercial third-party
   paper content are bundled.

## Backlog

### Maintenance First

- Keep dependency ranges healthy and watch for Streamlit or parser changes that
  affect the launcher path.
- Refresh screenshots only when the visible app changes enough to make old
  images misleading.
- Keep release notes and ZIP QA notes current for every public release.
- Review issue templates after the first outside bug reports arrive.

### Analyzer Quality

- Add synthetic benchmark cases only when a real false positive or false
  negative pattern is identified.
- Prefer reducing false positives before increasing catch rate.
- Keep calibration claims honest: synthetic benchmarks are guardrails, not proof
  of real-world accuracy.

### Public Demo Work

- Keep landmark/result-pack lists metadata-only: titles, source links, expected
  filenames, notes, and access/licensing reminders.
- Do not bundle third-party PDFs or copied paper text.
- Consider a small public demo results pack only after the legal/source access
  boundaries are double-checked.

### Packaging Later

- A proper installer or packaged desktop build can be considered later, but the
  current supported path remains GitHub ZIP plus `Start-Gauntlet.bat`.
- Any installer work should preserve the local-first, non-AI default and make
  workspace storage visible to the user.

## Not For The Next Release

- New app pages.
- More AI providers.
- A full PDF viewer.
- Bundled third-party paper PDFs.
- Broad analyzer rewrites without new calibration evidence.
- Commercial licensing automation inside the app.
