# The Gauntlet

The Gauntlet is a local, non-AI paper checker for stress-testing theories,
papers, and arguments. Upload a document and it produces a transparent
rule-based verdict: `RESOLVES`, `PARTIAL`, `FAILS`, or
`CREATES_NEW_PARADOXES`.

V1 does not call any AI provider. There is no OpenAI, Anthropic, Gemini,
Ollama, model selector, or API key setup. The app runs on your machine and uses
deterministic rules for claim extraction, contradiction checks, mechanism
checks, and evidence scoring.

## Quick Start on Windows

1. Download this repo from GitHub.
2. Unzip it.
3. Double-click `Start-Gauntlet.bat`.
4. Upload a `.pdf`, `.docx`, `.txt`, or `.md` paper.
5. Press `Analyze Paper`.

The launcher creates a local `.venv`, installs the requirements, and opens the
Streamlit app in your browser.

## Manual Start

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

On macOS or Linux, use the equivalent activation path for your shell.

## What the Verdict Means

- `RESOLVES`: the paper's detected claims include mechanisms and enough
  evidence markers to pass the v1 rule checks.
- `PARTIAL`: the paper has useful claim structure, but some mechanisms,
  evidence, or specificity are thin.
- `FAILS`: the rules did not find enough explicit claim, mechanism, and
  evidence support.
- `CREATES_NEW_PARADOXES`: the rules found a high-severity internal
  contradiction.

The verdict is a review aid, not a replacement for expert peer review.

## What V1 Checks

- explicit resolution claims
- mechanism language such as `because`, `through`, `via`, `framework`, or
  `equation`
- evidence markers such as data, observations, citations, numbers, equations,
  methodology terms, and statistical language
- internal contradictions, direct negations, property mismatches, universal
  counterexamples, and temporal conflicts
- exportable JSON and Markdown reports

## Legacy Colab Versions

The older Colab/prototype files are preserved in `legacy/colab-originals/`.
They are still available for people who want the original notebook-style
experiments or AI-wired versions.

## Development

```bash
python -m pip install -r requirements-dev.txt
pytest
```

The public Python entry point is:

```python
from gauntlet_core import analyze_paper_text

report = analyze_paper_text("Your paper text here", source_name="paper.txt")
print(report.verdict)
print(report.to_json())
```

## License

This project uses the Motion-TimeSpace Non-Commercial License. See `LICENSE`.
