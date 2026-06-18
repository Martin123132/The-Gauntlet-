# The Gauntlet v0.27.0 ZIP QA

Generated source ZIP smoke test completed on Windows on 2026-06-18.

## Source

- Release: [`v0.27.0`](https://github.com/Martin123132/The-Gauntlet-/releases/tag/v0.27.0)
- Archive type: GitHub generated source ZIP
- App entry point: `Start-Gauntlet.bat`

## Result

Pass. The release ZIP extracted cleanly, launched from a fresh folder, created
`.venv`, installed only `requirements.txt`, wrote
`.gauntlet/logs/Start-Gauntlet.log`, and started Streamlit at
`http://localhost:8501`.

## Smoke Coverage

- Summary loaded as the first page.
- `Start Here` panel rendered for a fresh session.
- Upload rail showed `Extraction Preview` and `Paste Text Instead`.
- `Try Sample Paper` produced a `PARTIAL` verdict.
- Sample analysis auto-saved to `.gauntlet/workspace/runs/`.
- Breakdown, Source Reader, Workspace, System Check, and Result Packs pages
  rendered from the generated ZIP.
- Workspace showed Reviewer Packet export controls.
- System Check exposed optional OCR readiness status.

## Notes

- First-run dependency installation can take a few minutes because Streamlit,
  parser libraries, and their transitive dependencies install into the local
  `.venv`.
- Optional OCR warnings are acceptable on the base ZIP install. OCR is not part
  of `requirements.txt` and is not required for normal local analysis.
- No API keys were used.
- No uploaded full paper file was saved during the smoke test.
