# The Gauntlet v0.28.0 ZIP QA

Generated source ZIP smoke test completed on Windows on 2026-06-28.

## Source

- Release: [`v0.28.0`](https://github.com/Martin123132/The-Gauntlet-/releases/tag/v0.28.0)
- Archive type: GitHub generated source ZIP
- App entry point: `Start-Gauntlet.bat`

## Result

Pass. The release ZIP downloaded from GitHub, extracted cleanly, launched from a
fresh folder, created `.venv`, installed only `requirements.txt`, wrote
`.gauntlet/logs/Start-Gauntlet.log`, and started Streamlit at
`http://localhost:8501`.

## Smoke Coverage

- Required public files were present, including `LICENSE`,
  `COMMERCIAL-LICENSE.md`, `NOTICE.md`, `README.md`, `requirements.txt`,
  `requirements-ai.txt`, `app.py`, v0.28 release notes, and screenshots.
- `Start-Gauntlet.bat` installed the local non-AI requirements only.
- Summary loaded with the `Start Here` panel and first-launch guidance.
- `Try Sample Paper` produced a `PARTIAL` verdict.
- Sample analysis auto-saved a workspace run.
- The app started from the generated release source, not from the development
  checkout.

## Notes

- First-run dependency installation can take a few minutes while Streamlit and
  parser dependencies install into `.venv`.
- Optional OCR warnings are acceptable on the base ZIP install. OCR is not part
  of `requirements.txt` and is not required for normal local analysis.
- No API keys were used.
- No uploaded full paper file was saved during the smoke test.
