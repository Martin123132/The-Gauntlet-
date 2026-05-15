# The Gauntlet Release Checklist

Use this checklist before merging `non-ai-app-v1` into `main` or publishing a release ZIP.

## Automated Checks

- [ ] Run `.venv\Scripts\python.exe -m pytest` locally.
- [ ] Confirm GitHub Actions passes on the branch or pull request.
- [ ] Confirm `Start-Gauntlet.bat` installs `requirements.txt`, not optional AI packages.

## Windows Download ZIP Check

- [ ] Download the branch or release as a ZIP.
- [ ] Extract the ZIP into a fresh folder with no existing `.venv`.
- [ ] Double-click `Start-Gauntlet.bat`.
- [ ] Confirm the launcher accepts Python 3.10 or newer.
- [ ] Confirm the launcher creates `.venv` and installs local requirements.
- [ ] Confirm the browser opens at `http://localhost:8501`.

## App Smoke Check

- [ ] Run the built-in sample paper.
- [ ] Confirm the Summary page shows a verdict.
- [ ] Confirm the Breakdown page shows claim audit and rule events.
- [ ] Run one Benchmark sample and confirm expected-vs-actual results.
- [ ] Open Refinement and confirm Gemini, OpenAI, and Anthropic provider choices are visible without installing AI dependencies.
- [ ] Export JSON and Markdown reports.

## Public Page Check

- [ ] README screenshots render on GitHub.
- [ ] README clearly says the normal checker is local and does not need an API key.
- [ ] Optional AI setup points to `requirements-ai.txt`.
- [ ] Legacy Colab files are still present under `legacy/colab-originals/`.
