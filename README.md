# The Gauntlet

The Gauntlet is a local-first paper checker for stress-testing theories,
papers, and arguments. Upload a document and it produces a transparent
rule-based verdict: `RESOLVES`, `PARTIAL`, `FAILS`, or
`CREATES_NEW_PARADOXES`.

The default flow does not call any AI provider. There is no API key setup for
the normal checker. The app runs on your machine and uses deterministic rules
for section parsing, claim extraction, contradiction checks, mechanism checks,
evidence linking, and verdict scoring.

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
  evidence markers to pass the v2 rule checks.
- `PARTIAL`: the paper has useful claim structure, but some mechanisms,
  evidence, or specificity are thin.
- `FAILS`: the rules did not find enough explicit claim, mechanism, and
  evidence support.
- `CREATES_NEW_PARADOXES`: the rules found a high-severity internal
  contradiction.

The verdict is a review aid, not a replacement for expert peer review.

## What V2 Checks

- document sections and claim locations
- explicit resolution claims
- mechanism language such as `because`, `through`, `via`, `framework`, or
  `equation`
- evidence markers and evidence links such as data, observations, citations,
  numbers, equations, methodology terms, and statistical language
- internal contradictions, direct negations, property mismatches, universal
  counterexamples, and temporal conflicts
- repair barriers such as unsupported resolution claims, missing mechanisms,
  evidence gaps, scope conflicts, circular support, and theory-as-fact wording
- exportable JSON and Markdown reports

## Optional Refinement Chamber

The `Refinement` page is optional. It lets a user paste session-only OpenAI and
Anthropic API keys, then runs a visible two-model critique:

1. The deterministic Gauntlet report creates an issue brief.
2. OpenAI proposes a critique and repair plan.
3. Anthropic challenges weak repairs, assumptions, and unresolved issues.
4. The combined repair plan is re-checked by the deterministic Gauntlet rules.

The app shows the prompts, returned model messages, disagreements, repair plan,
and re-check result. It does not ask for hidden model reasoning and it does not
save API keys to project files.

Install optional AI dependencies only if you want this page to run live:

```bash
.venv\Scripts\python -m pip install -r requirements-ai.txt
```

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

Optional refinement can be imported separately:

```python
from gauntlet_core import analyze_paper_text, run_refinement

report = analyze_paper_text(paper_text, source_name="paper.txt")
refinement = run_refinement(report, paper_text, openai_api_key="...", anthropic_api_key="...")
print(refinement.repair_plan)
```

## License

This project uses the Motion-TimeSpace Non-Commercial License. See `LICENSE`.
