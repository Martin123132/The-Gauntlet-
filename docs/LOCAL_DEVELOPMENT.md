# Local Development Storage Notes

These notes are for maintainer/local development. Public GitHub ZIP users do not need a special drive layout.

## Active Maintainer Checkout

For the current development pass, use:

```text
D:\Projects\The-Gauntlet-
```

Treat any older OneDrive or C-drive checkout as archive-only. Do not run tests,
Streamlit smoke checks, screenshots, generated reports, or release QA from the
archive checkout.

## D-Safe Runtime Convention

Keep project files, caches, temp output, Streamlit/test artifacts, screenshots,
local workspace data, and generated files on `D:\`.

Recommended local shell setup before test or smoke commands:

```powershell
$env:TEMP = "D:\Temp\gauntlet-codex"
$env:TMP = "D:\Temp\gauntlet-codex"
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
Set-Location D:\Projects\The-Gauntlet-
```

Normal ignored local outputs include:

- `.venv/`
- `.gauntlet/`
- `.pytest_cache/`
- `gauntlet-reports/`
- `artifacts/`
- `streamlit*.log`
- `ui-*.png`

## Validation Commands

Run from `D:\Projects\The-Gauntlet-`:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -c "from gauntlet_core.benchmarks import run_calibration_suite; result = run_calibration_suite(strict=True); print('gate=', result.gate.passed); print('overall=', result.pass_rate); print('guardrail=', result.guardrail_pass_rate)"
```

The default checker remains local-first and non-AI. Do not install
`requirements-ai.txt` unless you are deliberately testing the optional
Refinement page.

## Public ZIP Users

Public users can unzip the repository wherever they want. For privacy, they
should avoid OneDrive, Dropbox, or other synced folders if they do not want
local report JSON, source snippets, reviewer notes, or launcher logs to sync
through that service.
