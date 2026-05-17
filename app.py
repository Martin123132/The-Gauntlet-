from __future__ import annotations

import html

import streamlit as st

from gauntlet_core import analyze_loaded_document, analyze_paper_text
from gauntlet_core.benchmarks import list_benchmark_samples, run_benchmark_sample
from gauntlet_core.document_loader import SUPPORTED_EXTENSIONS, load_document_from_bytes
from gauntlet_core.models import source_reference
from gauntlet_core.refinement import (
    DEFAULT_CHALLENGER_PROVIDER,
    DEFAULT_CRITIC_PROVIDER,
    DEFAULT_PROVIDER_MODELS,
    PROVIDER_ORDER,
    ProviderSelection,
    RefinementError,
    run_provider_refinement,
)
from gauntlet_core.sample_text import SAMPLE_PAPER
from gauntlet_core.workspace import (
    REVIEW_STATUSES,
    delete_saved_run,
    list_saved_runs,
    load_saved_run,
    save_analysis_run,
    update_saved_run_notes,
    workspace_runs_dir,
)


st.set_page_config(page_title="The Gauntlet", page_icon="G", layout="wide")

VALID_PAGES = ("summary", "workspace", "breakdown", "benchmarks", "claims", "contradictions", "evidence", "refinement")
PAGE_LABELS = {
    "summary": "Summary",
    "workspace": "Workspace",
    "breakdown": "Breakdown",
    "benchmarks": "Benchmarks",
    "claims": "Claims",
    "contradictions": "Contradictions",
    "evidence": "Evidence",
    "refinement": "Refinement",
}


@st.cache_resource
def report_store() -> dict:
    return {}


CSS = """
<style>
:root {
  --gauntlet-bg: #f7f9fb;
  --gauntlet-panel: #ffffff;
  --gauntlet-ink: #14191f;
  --gauntlet-muted: #66717f;
  --gauntlet-soft: #eef3f6;
  --gauntlet-border: #dce4ea;
  --gauntlet-teal: #07877f;
  --gauntlet-teal-dark: #056f69;
  --gauntlet-amber: #d48806;
  --gauntlet-amber-bg: #fff5df;
  --gauntlet-red: #d92d20;
  --gauntlet-red-bg: #ffe8e6;
  --gauntlet-shadow: 0 14px 38px rgba(18, 34, 51, .08);
}
.stApp {
  background: var(--gauntlet-bg);
}
.main .block-container {
  padding-top: 0;
  padding-bottom: 1.1rem;
  max-width: 1540px;
}
[data-testid="stMainBlockContainer"] {
  padding: 0 1.25rem 1rem !important;
  max-width: 1680px;
}
[data-testid="stHeader"],
[data-testid="stToolbar"],
#MainMenu,
footer {
  visibility: hidden;
  height: 0;
}
h1, h2, h3, p {
  letter-spacing: 0;
}
[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--gauntlet-border);
  border-radius: 8px;
  background: white;
  box-shadow: var(--gauntlet-shadow);
}
.gauntlet-topbar {
  display: grid;
  grid-template-columns: 300px 1fr auto;
  align-items: center;
  min-height: 64px;
  margin: 0 -1.25rem 1rem -1.25rem;
  padding: 0 1.4rem;
  border-bottom: 1px solid var(--gauntlet-border);
  background: rgba(255, 255, 255, .94);
  position: sticky;
  top: 0;
  z-index: 5;
  backdrop-filter: blur(10px);
}
.brand-lockup {
  display: flex;
  align-items: center;
  gap: .7rem;
}
.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  background: #111820;
  color: white;
  font-weight: 850;
  font-size: 1rem;
}
.brand-lockup h1 {
  color: var(--gauntlet-ink);
  font-size: 1.45rem;
  font-weight: 820;
  margin: 0;
}
.nav-tabs {
  display: flex;
  align-items: stretch;
  height: 64px;
}
.nav-tab {
  display: flex;
  align-items: center;
  padding: 0 1.25rem;
  color: #252d38;
  font-weight: 680;
  font-size: .93rem;
  text-decoration: none;
  border-bottom: 3px solid transparent;
}
.nav-tab:hover {
  color: var(--gauntlet-teal);
  text-decoration: none;
}
.nav-tab.active {
  color: var(--gauntlet-teal);
  border-bottom: 3px solid var(--gauntlet-teal);
  background: linear-gradient(180deg, rgba(7,135,127,.07), rgba(7,135,127,0));
}
.top-actions {
  display: flex;
  align-items: center;
  gap: .8rem;
  color: var(--gauntlet-muted);
}
.export-chip {
  border: 1px solid var(--gauntlet-border);
  border-radius: 7px;
  padding: .62rem .9rem;
  font-weight: 700;
  color: #26313d;
  background: white;
}
.panel-title {
  color: var(--gauntlet-ink);
  font-size: 1.02rem;
  font-weight: 780;
  margin: 0 0 .7rem 0;
}
.small-label {
  color: var(--gauntlet-muted);
  font-size: .78rem;
  font-weight: 720;
  text-transform: uppercase;
  letter-spacing: .04em;
}
[data-testid="stFileUploader"] section {
  border: 1.5px dashed #aeb9c4;
  border-radius: 8px;
  background: #fbfcfd;
  min-height: 142px;
  display: flex;
  align-items: center;
}
[data-testid="stFileUploader"] small {
  color: var(--gauntlet-muted);
}
.document-card,
.options-card,
.verdict-panel,
.breakdown-card,
.takeaway-card,
.finding-card {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: white;
}
.document-card,
.options-card {
  padding: .8rem .9rem;
  margin-top: .85rem;
}
.doc-row {
  display: flex;
  justify-content: space-between;
  gap: .8rem;
  color: #2c3540;
  font-size: .84rem;
  margin: .42rem 0;
}
div[data-testid="stButton"] > button {
  min-height: 3.08rem;
  border-radius: 6px;
  font-weight: 820;
}
div[data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, var(--gauntlet-teal), var(--gauntlet-teal-dark));
  border: 0;
}
div[data-testid="stDownloadButton"] > button {
  border-radius: 7px;
  border-color: var(--gauntlet-border);
  font-weight: 760;
}
button[data-baseweb="tab"] {
  font-weight: 700;
}
button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--gauntlet-teal);
}
div[data-baseweb="tab-highlight"] {
  background-color: var(--gauntlet-teal);
}
.local-note {
  color: var(--gauntlet-muted);
  font-size: .82rem;
  text-align: center;
  margin-top: .8rem;
}
.verdict-panel {
  padding: 1rem 1rem 1.15rem;
  box-shadow: var(--gauntlet-shadow);
  margin-bottom: .9rem;
}
.verdict-label {
  color: var(--gauntlet-ink);
  font-size: 1rem;
  font-weight: 780;
  margin-bottom: .75rem;
}
.verdict-hero {
  display: grid;
  grid-template-columns: minmax(210px, 280px) 1fr;
  gap: 1.4rem;
  align-items: center;
}
.verdict-stamp {
  border: 1px solid var(--gauntlet-amber);
  border-radius: 8px;
  background: linear-gradient(135deg, #fffaf0, #fff2d7);
  color: var(--gauntlet-ink);
  font-size: 2.2rem;
  font-weight: 850;
  line-height: 1;
  text-align: center;
  padding: 1.55rem .8rem;
}
.verdict-stamp.resolves {
  border-color: var(--gauntlet-teal);
  background: linear-gradient(135deg, #eefbf8, #ddf7f2);
}
.verdict-stamp.fails,
.verdict-stamp.creates_new_paradoxes {
  border-color: var(--gauntlet-red);
  background: linear-gradient(135deg, #fff1f0, #ffe4e2);
}
.verdict-copy {
  color: #232b35;
  font-size: 1rem;
  line-height: 1.48;
}
.verdict-meta {
  display: flex;
  gap: 1.05rem;
  flex-wrap: wrap;
  margin-top: 1rem;
  color: #1d2630;
  font-weight: 740;
}
.verdict-meta span {
  color: var(--gauntlet-amber);
  margin-left: .35rem;
}
.stat-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: white;
  margin: .9rem 0;
  overflow: hidden;
}
.stat-tile {
  padding: 1rem .95rem;
  min-height: 118px;
  border-right: 1px solid var(--gauntlet-border);
}
.stat-tile:last-child {
  border-right: 0;
}
.stat-title {
  color: #273340;
  font-size: .82rem;
  font-weight: 700;
  margin-bottom: .55rem;
}
.stat-number {
  color: #101820;
  font-size: 1.55rem;
  font-weight: 850;
}
.stat-note {
  color: var(--gauntlet-teal);
  font-size: .78rem;
  margin-top: .4rem;
}
.breakdown-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .8rem;
  margin-bottom: .9rem;
}
.breakdown-card {
  padding: 1rem;
  min-height: 198px;
}
.takeaway-card {
  padding: .9rem 1rem;
  margin-bottom: .9rem;
}
.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .8rem;
  margin: .9rem 0;
}
.detail-card,
.wide-detail-card,
.claim-card {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: white;
  box-shadow: var(--gauntlet-shadow);
}
.detail-card {
  padding: 1rem;
}
.wide-detail-card {
  padding: 1rem;
  margin-bottom: .9rem;
}
.detail-title {
  color: var(--gauntlet-ink);
  font-weight: 820;
  font-size: 1.25rem;
  margin-bottom: .25rem;
}
.detail-subtitle {
  color: var(--gauntlet-muted);
  font-size: .92rem;
  margin-bottom: .9rem;
}
.claim-card {
  padding: .95rem 1rem;
  margin-bottom: .7rem;
}
.claim-head {
  display: flex;
  justify-content: space-between;
  gap: .8rem;
  align-items: center;
  margin-bottom: .45rem;
}
.claim-status {
  border-radius: 6px;
  padding: .18rem .52rem;
  background: #e6f6f3;
  color: var(--gauntlet-teal);
  font-size: .76rem;
  font-weight: 850;
  text-transform: uppercase;
}
.claim-status.partial {
  background: var(--gauntlet-amber-bg);
  color: var(--gauntlet-amber);
}
.claim-status.failed {
  background: var(--gauntlet-red-bg);
  color: var(--gauntlet-red);
}
.claim-text {
  color: #24303c;
  line-height: 1.48;
}
.claim-meta {
  color: var(--gauntlet-muted);
  font-size: .84rem;
  margin-top: .45rem;
}
.empty-detail {
  border: 1px dashed #b8c5cf;
  border-radius: 8px;
  background: #fbfcfd;
  padding: 1.25rem;
  color: var(--gauntlet-muted);
}
.bar-row {
  display: grid;
  grid-template-columns: 96px 1fr 42px;
  gap: .65rem;
  align-items: center;
  margin: .68rem 0;
  font-size: .84rem;
}
.bar-track {
  height: 7px;
  background: #e9edf1;
  border-radius: 99px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 99px;
  background: var(--gauntlet-teal);
}
.bar-fill.amber {
  background: var(--gauntlet-amber);
}
.bar-fill.red {
  background: var(--gauntlet-red);
}
.donut-lite {
  width: 130px;
  height: 130px;
  border-radius: 50%;
  margin: .65rem auto;
  background: conic-gradient(var(--gauntlet-teal) 0 45%, var(--gauntlet-amber) 45% 78%, var(--gauntlet-red) 78% 100%);
  position: relative;
}
.donut-lite::after {
  content: "";
  position: absolute;
  inset: 30px;
  border-radius: 50%;
  background: white;
}
.donut-center {
  position: relative;
  margin-top: -86px;
  text-align: center;
  font-weight: 850;
  font-size: 1.35rem;
}
.donut-caption {
  position: relative;
  text-align: center;
  color: var(--gauntlet-muted);
  font-size: .75rem;
  margin-bottom: .8rem;
}
.filter-row {
  display: flex;
  gap: .55rem;
  margin: .75rem 0 1rem;
  flex-wrap: wrap;
}
.filter-pill {
  border: 1px solid var(--gauntlet-border);
  border-radius: 6px;
  padding: .34rem .7rem;
  font-size: .82rem;
  font-weight: 740;
  background: #f9fbfc;
}
.filter-pill.active {
  color: white;
  border-color: var(--gauntlet-teal);
  background: linear-gradient(135deg, var(--gauntlet-teal), var(--gauntlet-teal-dark));
}
.filter-pill.high {
  color: var(--gauntlet-red);
  background: #fff0ef;
}
.filter-pill.medium {
  color: var(--gauntlet-amber);
  background: #fff7e8;
}
.finding-card {
  border-left: 4px solid var(--gauntlet-amber);
  padding: .85rem .85rem .8rem;
  margin-bottom: .75rem;
  box-shadow: 0 10px 24px rgba(22, 34, 44, .05);
}
.finding-card.high {
  border-left-color: var(--gauntlet-red);
}
.finding-card.low {
  border-left-color: var(--gauntlet-teal);
}
.finding-title {
  color: var(--gauntlet-ink);
  font-weight: 760;
  margin-bottom: .2rem;
  display: flex;
  justify-content: space-between;
  gap: .7rem;
}
.severity-pill {
  border-radius: 6px;
  padding: .18rem .5rem;
  font-size: .75rem;
  font-weight: 800;
  background: var(--gauntlet-amber-bg);
  color: var(--gauntlet-amber);
  white-space: nowrap;
}
.severity-pill.high {
  background: var(--gauntlet-red-bg);
  color: var(--gauntlet-red);
}
.severity-pill.low {
  background: #e6f6f3;
  color: var(--gauntlet-teal);
}
.finding-meta {
  color: var(--gauntlet-muted);
  font-size: .82rem;
  margin-bottom: .55rem;
}
.finding-body {
  color: #293442;
  font-size: .92rem;
}
.repair-button-look {
  display: inline-block;
  border: 1px solid var(--gauntlet-teal);
  color: var(--gauntlet-teal);
  border-radius: 6px;
  padding: .32rem .55rem;
  font-weight: 760;
  font-size: .78rem;
  margin-top: .35rem;
}
.muted-note {
  color: var(--gauntlet-muted);
  font-size: .92rem;
}
.audit-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .75rem;
  margin-bottom: .9rem;
}
.audit-card,
.evidence-link-card,
.turn-card {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: white;
  padding: .85rem .95rem;
  box-shadow: 0 10px 24px rgba(22, 34, 44, .05);
}
.audit-card strong,
.evidence-link-card strong,
.turn-card strong {
  color: var(--gauntlet-ink);
}
.audit-card span {
  color: var(--gauntlet-teal);
  font-weight: 820;
}
.source-ref {
  display: inline-block;
  border: 1px solid #c7e2df;
  border-radius: 6px;
  background: #effaf8;
  color: var(--gauntlet-teal);
  font-size: .76rem;
  font-weight: 800;
  padding: .2rem .48rem;
  margin-top: .4rem;
}
.source-snippet {
  border-left: 3px solid var(--gauntlet-teal);
  background: #fbfcfd;
  color: #273340;
  padding: .6rem .75rem;
  margin: .45rem 0;
}
.rubric-row {
  display: grid;
  grid-template-columns: 150px 1fr 58px;
  gap: .65rem;
  align-items: center;
  margin: .62rem 0;
  color: #273340;
  font-size: .84rem;
}
.mini-list {
  margin: .5rem 0 0 0;
  padding-left: 1rem;
  color: var(--gauntlet-muted);
  font-size: .84rem;
}
.refinement-lock {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: linear-gradient(135deg, #ffffff, #f4f8fa);
  padding: 1rem;
  margin-bottom: .9rem;
}
.transcript-box {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: #fbfcfd;
  padding: .9rem;
  color: #26313d;
  white-space: pre-wrap;
  max-height: 420px;
  overflow: auto;
}
.benchmark-hero {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: white;
  box-shadow: var(--gauntlet-shadow);
  padding: 1rem;
  margin-bottom: .9rem;
}
.benchmark-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .85rem;
  margin-bottom: .9rem;
}
.benchmark-card {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: white;
  padding: 1rem;
  min-height: 150px;
}
.match-pill {
  display: inline-block;
  border-radius: 6px;
  padding: .22rem .55rem;
  font-size: .76rem;
  font-weight: 850;
  text-transform: uppercase;
  background: #e6f6f3;
  color: var(--gauntlet-teal);
}
.match-pill.review {
  background: var(--gauntlet-amber-bg);
  color: var(--gauntlet-amber);
}
.comparison-list {
  margin: .65rem 0 0;
  padding-left: 1.05rem;
  color: #273340;
  font-size: .86rem;
}
.workspace-grid {
  display: grid;
  grid-template-columns: minmax(280px, .36fr) minmax(0, .64fr);
  gap: .9rem;
}
.workspace-card {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: white;
  padding: .95rem;
  margin-bottom: .75rem;
  box-shadow: 0 10px 24px rgba(22, 34, 44, .05);
}
.workspace-card.active {
  border-color: #9fd3cf;
  background: #fbfffe;
}
.workspace-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .5rem;
  margin-top: .75rem;
  color: var(--gauntlet-muted);
  font-size: .84rem;
}
.workspace-meta strong {
  display: block;
  color: var(--gauntlet-ink);
  font-size: 1rem;
}
.workspace-privacy {
  border: 1px solid #c7e2df;
  border-radius: 8px;
  background: #effaf8;
  color: #24423f;
  padding: .85rem .95rem;
  margin-bottom: .9rem;
}
.compare-table {
  width: 100%;
  border-collapse: collapse;
  margin: .8rem 0;
  color: #273340;
  font-size: .9rem;
}
.compare-table th,
.compare-table td {
  border-bottom: 1px solid var(--gauntlet-border);
  padding: .55rem .4rem;
  text-align: left;
}
.compare-table th {
  color: var(--gauntlet-muted);
  font-size: .78rem;
  text-transform: uppercase;
}
.footer-status {
  display: grid;
  grid-template-columns: 300px 1fr 250px;
  gap: 1rem;
  align-items: center;
  margin: 1rem -1.25rem -1.1rem;
  padding: .9rem 1.4rem;
  background: white;
  border-top: 1px solid var(--gauntlet-border);
  color: var(--gauntlet-muted);
  font-size: .82rem;
}
@media (max-width: 1050px) {
  .gauntlet-topbar {
    grid-template-columns: 1fr;
    gap: .5rem;
    padding: .9rem 1rem;
  }
  .nav-tabs {
    height: auto;
    flex-wrap: wrap;
  }
  .nav-tab {
    padding: .45rem .75rem;
  }
  .verdict-hero,
  .breakdown-grid,
  .audit-grid,
  .benchmark-grid,
  .workspace-grid,
  .detail-grid,
  .stat-strip,
  .footer-status {
    grid-template-columns: 1fr;
  }
  .stat-tile {
    border-right: 0;
    border-bottom: 1px solid var(--gauntlet-border);
  }
}
</style>
"""


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    page = current_page()
    report = active_report()
    render_topbar(page)

    if page == "summary":
        render_summary_page(report)
    elif page == "workspace":
        render_workspace_page()
    elif page == "benchmarks":
        render_benchmarks_page()
    else:
        left, detail = st.columns([0.23, 0.77], gap="medium")
        with left:
            render_upload_panel()
        with detail:
            render_detail_page(page, report)

    render_footer(report)


def current_page() -> str:
    page = st.query_params.get("page", "summary")
    if isinstance(page, list):
        page = page[0] if page else "summary"
    return page if page in VALID_PAGES else "summary"


def active_report():
    if "report" in st.session_state:
        return st.session_state["report"]
    return report_store().get("report")


def active_source_text() -> str:
    if "paper_text" in st.session_state:
        return st.session_state["paper_text"]
    return report_store().get("paper_text", "")


def active_refinement():
    if "refinement_report" in st.session_state:
        return st.session_state["refinement_report"]
    return report_store().get("refinement_report")


def active_benchmark_result():
    if "benchmark_result" in st.session_state:
        return st.session_state["benchmark_result"]
    return report_store().get("benchmark_result")


def save_report(report, paper_text: str, run_kind: str = "analysis", benchmark_result=None) -> None:
    st.session_state["report"] = report
    st.session_state["paper_text"] = paper_text
    st.session_state.pop("refinement_report", None)
    if benchmark_result is None:
        st.session_state.pop("benchmark_result", None)
    report_store()["report"] = report
    report_store()["paper_text"] = paper_text
    report_store().pop("refinement_report", None)
    if benchmark_result is None:
        report_store().pop("benchmark_result", None)
    try:
        saved_run = save_analysis_run(report, run_kind=run_kind, benchmark_result=benchmark_result)
    except OSError as exc:
        st.warning(f"Analysis finished, but the local workspace could not save this run: {exc}")
        return
    st.session_state["workspace_run_id"] = saved_run.run_id
    report_store()["workspace_run_id"] = saved_run.run_id


def open_saved_run(saved_run) -> None:
    st.session_state["report"] = saved_run.report
    st.session_state["paper_text"] = ""
    st.session_state["workspace_run_id"] = saved_run.run_id
    st.session_state.pop("refinement_report", None)
    st.session_state.pop("benchmark_result", None)
    report_store()["report"] = saved_run.report
    report_store()["paper_text"] = ""
    report_store()["workspace_run_id"] = saved_run.run_id
    report_store().pop("refinement_report", None)
    report_store().pop("benchmark_result", None)


def save_refinement(refinement_report) -> None:
    st.session_state["refinement_report"] = refinement_report
    report_store()["refinement_report"] = refinement_report


def save_benchmark_result(benchmark_result) -> None:
    st.session_state["benchmark_result"] = benchmark_result
    report_store()["benchmark_result"] = benchmark_result


def render_topbar(active_page: str) -> None:
    nav = "\n".join(
        f'<a class="nav-tab {"active" if page == active_page else ""}" href="?page={page}" target="_self">{label}</a>'
        for page, label in PAGE_LABELS.items()
    )
    st.markdown(
        f"""
        <div class="gauntlet-topbar">
          <div class="brand-lockup">
            <div class="brand-mark">G</div>
            <h1>The Gauntlet</h1>
          </div>
          <div class="nav-tabs">
            {nav}
          </div>
          <div class="top-actions">
            <a class="export-chip" href="?page=breakdown" target="_self">Export Report</a>
            <div style="font-size: 1.35rem; line-height: 1;">=</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary_page(report) -> None:
    left, middle, right = st.columns([0.23, 0.43, 0.34], gap="medium")
    with left:
        render_upload_panel()
    with middle:
        if report:
            render_report_center(report)
        else:
            render_empty_state()
    with right:
        render_flagged_panel(report)


def render_upload_panel() -> None:
    with st.container(border=True):
        st.markdown('<div class="panel-title">1. Upload Paper</div>', unsafe_allow_html=True)
        upload = st.file_uploader(
            "Choose a paper",
            type=[extension.lstrip(".") for extension in sorted(SUPPORTED_EXTENSIONS)],
            label_visibility="collapsed",
        )

        render_document_info(upload)

        st.markdown('<div class="options-card">', unsafe_allow_html=True)
        st.markdown('<div class="small-label">Analysis options</div>', unsafe_allow_html=True)
        st.selectbox("Rule set", ["Standard (Default)"], label_visibility="visible")
        st.selectbox("Strictness", ["Normal", "Strict", "Lenient"], label_visibility="visible")
        use_sample = st.toggle("Use built-in sample paper", value=False)
        st.markdown("</div>", unsafe_allow_html=True)

        analyze_clicked = st.button("Analyze Paper", type="primary", use_container_width=True)
        if analyze_clicked:
            try:
                run_kind = "analysis"
                if use_sample:
                    paper_text = SAMPLE_PAPER
                    report = analyze_paper_text(paper_text, source_name="sample-paper.txt")
                    run_kind = "sample"
                elif upload is not None:
                    loaded_document = load_document_from_bytes(upload.name, upload.getvalue())
                    paper_text = loaded_document.text
                    if not paper_text.strip():
                        st.error("No readable text was found in that file.")
                        return
                    report = analyze_loaded_document(loaded_document)
                else:
                    st.error("Upload a paper or turn on the sample paper first.")
                    return
            except Exception as exc:  # Streamlit should show clean user-facing errors.
                st.error(str(exc))
                return
            save_report(report, paper_text, run_kind=run_kind)
            st.rerun()

        st.markdown(
            '<p class="local-note">Analysis is 100% local. Completed reports auto-save under .gauntlet/workspace/runs/ without saving the uploaded file.</p>',
            unsafe_allow_html=True,
        )


def render_document_info(upload) -> None:
    filename = upload.name if upload else "No file selected"
    size = f"{upload.size / 1024:.1f} KB" if upload else "-"
    st.markdown(
        f"""
        <div class="document-card">
          <div class="small-label">Document info</div>
          <div class="doc-row"><span>File</span><strong>{html.escape(filename)}</strong></div>
          <div class="doc-row"><span>Size</span><strong>{html.escape(size)}</strong></div>
          <div class="doc-row"><span>Supported</span><strong>PDF, TXT, DOCX, MD</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="verdict-panel">
          <div class="verdict-label">Verdict</div>
          <div class="verdict-hero">
            <div class="verdict-stamp">READY</div>
            <div class="verdict-copy">Upload a paper or use the built-in sample to generate a local verdict. The report will appear here with claim counts, evidence quality, contradictions, and export options.</div>
          </div>
        </div>
        <div class="stat-strip">
          <div class="stat-tile"><div class="stat-title">Claims Made</div><div class="stat-number">-</div><div class="stat-note">Waiting for analysis</div></div>
          <div class="stat-tile"><div class="stat-title">Supported Claims</div><div class="stat-number">-</div><div class="stat-note">Local rules only</div></div>
          <div class="stat-tile"><div class="stat-title">Internal Contradictions</div><div class="stat-number">-</div><div class="stat-note">No paper loaded</div></div>
          <div class="stat-tile"><div class="stat-title">Evidence Quality</div><div class="stat-number">-</div><div class="stat-note">0 to 1 score</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_report_center(report) -> None:
    stamp_class = report.verdict.lower()
    st.markdown(
        f"""
        <div class="verdict-panel">
          <div class="verdict-label">Verdict</div>
          <div class="verdict-hero">
            <div class="verdict-stamp {html.escape(stamp_class)}">{html.escape(report.verdict)}</div>
            <div>
              <div class="verdict-copy">{html.escape(report.summary)}</div>
              <div class="verdict-meta">
                <div>Confidence:<span>{report.confidence:.0%}</span></div>
                <div>Evidence Quality:<span>{evidence_label(report.evidence.score)}</span></div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_stat_strip(report)
    render_breakdowns(report)
    st.markdown(
        '<a class="export-chip" href="?page=breakdown" target="_self">Open full breakdown</a>',
        unsafe_allow_html=True,
    )


def render_detail_page(page: str, report) -> None:
    if page == "benchmarks":
        render_benchmarks_page()
        return

    if not report:
        render_missing_report(page)
        return

    if page == "breakdown":
        render_breakdown_page(report)
    elif page == "claims":
        render_claims_page(report)
    elif page == "contradictions":
        render_contradictions_page(report)
    elif page == "evidence":
        render_evidence_page(report)
    elif page == "refinement":
        render_refinement_page(report)
    else:
        render_breakdown_page(report)


def render_missing_report(page: str) -> None:
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">{html.escape(PAGE_LABELS.get(page, "Breakdown"))}</div>
          <div class="detail-subtitle">Run an analysis first, then this page will show the detailed breakdown.</div>
          <div class="empty-detail">Use the upload rail on the left or turn on the built-in sample paper, then press Analyze Paper.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_breakdown_page(report) -> None:
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">Actual Breakdown</div>
          <div class="detail-subtitle">Source: {html.escape(report.source_name)}. This page expands the front-page verdict into the claim audit, contradiction ledger, and evidence profile.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_stat_strip(report)
    render_breakdowns(report)
    render_curtain_up(report)
    render_claims_page(report, compact=True)
    render_contradictions_page(report, compact=True)
    render_evidence_page(report, compact=True)
    render_exports(report)


def render_curtain_up(report) -> None:
    st.markdown(
        """
        <div class="wide-detail-card">
          <div class="detail-title">Curtain-Up Audit</div>
          <div class="detail-subtitle">The visible rule trail behind the verdict: rubric weights, parsing events, and linked evidence snippets.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    rubric_rows = []
    for item in report.verdict_rubric:
        pct = int(min(100, max(0, item.score * 100)))
        rubric_rows.append(
            f"""
            <div class="rubric-row">
              <span>{html.escape(item.name)}</span>
              <div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>
              <strong>{item.score:.2f}</strong>
            </div>
            <div class="muted-note">{html.escape(item.reason)} | Weight {item.weight:.2f}</div>
            """
        )
    event_cards = []
    for event in report.audit_events:
        score = "" if event.score is None else f" <span>{event.score:.2f}</span>"
        event_cards.append(
            f"""
            <div class="audit-card">
              <strong>{html.escape(event.step.title())}</strong>{score}
              <div class="muted-note">{html.escape(event.status)} - {html.escape(event.detail)}</div>
            </div>
            """
        )
    evidence_cards = []
    for link in report.evidence.evidence_links[:6]:
        evidence_cards.append(
            f"""
            <div class="evidence-link-card">
              <strong>{html.escape(link.id)} - {html.escape(link.type.title())}</strong>
              <div class="muted-note">{html.escape(link.section)} | Sentence {link.sentence_index} | Confidence {link.confidence:.0%}</div>
              <div class="source-ref">{html.escape(source_reference(link.source_span))}</div>
              <div class="claim-text">{html.escape(link.snippet)}</div>
            </div>
            """
        )
    st.markdown(
        f"""
        <div class="breakdown-grid">
          <div class="breakdown-card">
            <div class="panel-title">Verdict Rubric</div>
            {''.join(rubric_rows) or '<div class="muted-note">No rubric details recorded.</div>'}
          </div>
          <div class="breakdown-card">
            <div class="panel-title">Evidence Index</div>
            <div class="muted-note">{report.evidence.linked_evidence} evidence snippets were indexed across {len(report.evidence.section_counts)} sections.</div>
            <ul class="mini-list">
              {''.join(f'<li>{html.escape(section)}: {count}</li>' for section, count in report.evidence.section_counts.items()) or '<li>No evidence snippets indexed.</li>'}
            </ul>
          </div>
        </div>
        <div class="audit-grid">
          {''.join(event_cards)}
        </div>
        <div class="audit-grid">
          {''.join(evidence_cards) or '<div class="empty-detail">No evidence snippets were indexed.</div>'}
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_source_trace(report, limit=10)


def render_claims_page(report, compact: bool = False) -> None:
    title = "Claim-by-Claim Audit" if compact else "Claims"
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">{title}</div>
          <div class="detail-subtitle">Each claim is scored for mechanism, evidence strength, and gaps the paper should repair.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not report.claims:
        st.markdown('<div class="empty-detail">No explicit resolution claims were detected.</div>', unsafe_allow_html=True)
        return
    for index, claim in enumerate(report.claims, start=1):
        render_claim_card(index, claim)


def render_claim_card(index: int, claim) -> None:
    gaps = ", ".join(claim.gaps) if claim.gaps else "none"
    status_class = html.escape(claim.status)
    evidence_links = ", ".join(link.id for link in claim.evidence_links) if claim.evidence_links else "none"
    rubric = "".join(
        f'<li>{html.escape(score.name)}: {score.score:.2f} - {html.escape(score.reason)}</li>'
        for score in claim.rubric_scores
    )
    audit = "".join(
        f'<li>{html.escape(event.step)}: {html.escape(event.status)} - {html.escape(event.detail)}</li>'
        for event in claim.audit_events
    )
    st.markdown(
        f"""
        <div class="claim-card">
          <div class="claim-head">
            <strong>{html.escape(claim.id or f"Claim {index}")} | {html.escape(claim.section)}</strong>
            <span class="claim-status {status_class}">{html.escape(claim.status)}</span>
          </div>
          <div class="claim-text">{html.escape(claim.claim)}</div>
          <div class="source-ref">{html.escape(source_reference(claim.source_span))}</div>
          <div class="claim-meta">Quality: {claim.quality:.2f} | Evidence: {claim.evidence_strength:.2f} | Mechanism: {html.escape(claim.mechanism)} | Gaps: {html.escape(gaps)} | Links: {html.escape(evidence_links)}</div>
          <div class="claim-meta"><strong>Repair:</strong> {html.escape(claim.repair_suggestion)}</div>
          <ul class="mini-list">{rubric}</ul>
          <ul class="mini-list">{audit}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    claim_label = claim.id or f"Claim {index}"
    render_source_expander(f"Source for {claim_label}", claim.source_span, claim.evidence_links)


def render_contradictions_page(report, compact: bool = False) -> None:
    title = "Contradiction Ledger" if compact else "Contradictions"
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">{title}</div>
          <div class="detail-subtitle">Internal contradictions and logical repair suggestions found by the deterministic rule set.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not report.findings:
        st.markdown(
            '<div class="finding-card low"><div class="finding-title">No internal contradictions <span class="severity-pill low">Low</span></div><div class="finding-body">The v2 rule set did not find direct internal conflicts in this paper.</div></div>',
            unsafe_allow_html=True,
        )
        return
    for finding in report.findings:
        render_finding(finding)


def render_evidence_page(report, compact: bool = False) -> None:
    title = "Evidence Profile" if compact else "Evidence"
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">{title}</div>
          <div class="detail-subtitle">Evidence quality is based on local markers: quantities, citations, math, method terms, and evidence language.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min(report.evidence.score, 1.0), text=f"Evidence quality {report.evidence.score:.2f}/1.00")
    st.markdown(
        f"""
        <div class="detail-grid">
          <div class="detail-card"><div class="stat-title">Quantitative Evidence</div><div class="stat-number">{report.evidence.quantitative_evidence}</div></div>
          <div class="detail-card"><div class="stat-title">Mathematical Content</div><div class="stat-number">{report.evidence.mathematical_content}</div></div>
          <div class="detail-card"><div class="stat-title">Citations</div><div class="stat-number">{report.evidence.citations}</div></div>
        </div>
        <div class="wide-detail-card">
          <div class="bar-row"><span>Data</span><div class="bar-track"><div class="bar-fill" style="width:{min(100, report.evidence.evidence_terms * 10)}%"></div></div><strong>{report.evidence.evidence_terms}</strong></div>
          <div class="bar-row"><span>Math</span><div class="bar-track"><div class="bar-fill amber" style="width:{min(100, report.evidence.mathematical_content * 14)}%"></div></div><strong>{report.evidence.mathematical_content}</strong></div>
          <div class="bar-row"><span>Citations</span><div class="bar-track"><div class="bar-fill" style="width:{min(100, report.evidence.citations * 18)}%"></div></div><strong>{report.evidence.citations}</strong></div>
          <div class="bar-row"><span>Methods</span><div class="bar-track"><div class="bar-fill red" style="width:{min(100, report.evidence.methodology_terms * 12)}%"></div></div><strong>{report.evidence.methodology_terms}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if report.evidence.evidence_links:
        for link in report.evidence.evidence_links:
            st.markdown(
                f"""
                <div class="evidence-link-card">
                  <strong>{html.escape(link.id)} - {html.escape(link.type.title())}</strong>
                  <div class="muted-note">{html.escape(link.section)} | Sentence {link.sentence_index} | Confidence {link.confidence:.0%}</div>
                  <div class="source-ref">{html.escape(source_reference(link.source_span))}</div>
                  <div class="claim-text">{html.escape(link.snippet)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            render_source_expander(f"Source for {link.id}", link.source_span)
    if not compact:
        render_source_trace(report, limit=18)


def render_stat_strip(report) -> None:
    high = sum(1 for finding in report.findings if finding.severity == "high")
    medium = sum(1 for finding in report.findings if finding.severity == "medium")
    contradiction_color = "var(--gauntlet-red)" if report.findings else "var(--gauntlet-teal)"
    st.markdown(
        f"""
        <div class="stat-strip">
          <div class="stat-tile">
            <div class="stat-title">Claims Made</div>
            <div class="stat-number">{len(report.claims)}</div>
            <div class="stat-note">Failed: {report.failed_claims}</div>
          </div>
          <div class="stat-tile">
            <div class="stat-title">Supported Claims</div>
            <div class="stat-number">{report.resolved_claims}</div>
            <div class="stat-note">Partial: {report.partial_claims}</div>
          </div>
          <div class="stat-tile">
            <div class="stat-title">Internal Contradictions</div>
            <div class="stat-number" style="color:{contradiction_color};">{len(report.findings)}</div>
            <div class="stat-note" style="color:var(--gauntlet-amber);">High: {high} - Medium: {medium}</div>
          </div>
          <div class="stat-tile">
            <div class="stat-title">Evidence Quality</div>
            <div class="stat-number">{report.evidence.score:.2f}</div>
            <div class="stat-note">{evidence_label(report.evidence.score)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_breakdowns(report) -> None:
    total = max(1, len(report.claims))
    supported_pct = int(report.resolved_claims / total * 100)
    partial_pct = int(report.partial_claims / total * 100)
    failed_pct = max(0, 100 - supported_pct - partial_pct)
    st.markdown(
        f"""
        <div class="breakdown-grid">
          <div class="breakdown-card">
            <div class="panel-title">Verdict Breakdown</div>
            <div class="donut-lite"></div>
            <div class="donut-center">{len(report.claims)}</div>
            <div class="donut-caption">Total Claims</div>
            <div class="bar-row"><span>Supported</span><div class="bar-track"><div class="bar-fill" style="width:{supported_pct}%"></div></div><strong>{supported_pct}%</strong></div>
            <div class="bar-row"><span>Partial</span><div class="bar-track"><div class="bar-fill amber" style="width:{partial_pct}%"></div></div><strong>{partial_pct}%</strong></div>
            <div class="bar-row"><span>Failed</span><div class="bar-track"><div class="bar-fill red" style="width:{failed_pct}%"></div></div><strong>{failed_pct}%</strong></div>
          </div>
          <div class="breakdown-card">
            <div class="panel-title">Evidence Quality Breakdown</div>
            <div class="bar-row"><span>Data</span><div class="bar-track"><div class="bar-fill" style="width:{min(100, report.evidence.evidence_terms * 10)}%"></div></div><strong>{report.evidence.evidence_terms}</strong></div>
            <div class="bar-row"><span>Math</span><div class="bar-track"><div class="bar-fill amber" style="width:{min(100, report.evidence.mathematical_content * 14)}%"></div></div><strong>{report.evidence.mathematical_content}</strong></div>
            <div class="bar-row"><span>Citations</span><div class="bar-track"><div class="bar-fill" style="width:{min(100, report.evidence.citations * 18)}%"></div></div><strong>{report.evidence.citations}</strong></div>
            <div class="bar-row"><span>Methods</span><div class="bar-track"><div class="bar-fill red" style="width:{min(100, report.evidence.methodology_terms * 12)}%"></div></div><strong>{report.evidence.methodology_terms}</strong></div>
          </div>
        </div>
        <div class="takeaway-card">
          <div class="panel-title">Key Takeaway</div>
          <div class="muted-note">{html.escape(report.summary)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_exports(report) -> None:
    json_col, markdown_col = st.columns(2)
    json_col.download_button(
        "Export JSON",
        data=report.to_json(),
        file_name=f"{safe_stem(report.source_name)}-gauntlet-report.json",
        mime="application/json",
        use_container_width=True,
    )
    markdown_col.download_button(
        "Export Markdown",
        data=report.to_markdown(),
        file_name=f"{safe_stem(report.source_name)}-gauntlet-report.md",
        mime="text/markdown",
        use_container_width=True,
    )


def render_benchmarks_page() -> None:
    samples = list_benchmark_samples()
    sample_by_title = {sample.title: sample for sample in samples}
    st.markdown(
        """
        <div class="benchmark-hero">
          <div class="detail-title">Benchmark Demo Gallery</div>
          <div class="detail-subtitle">Synthetic papers with known expected outcomes. Run one to see whether the current deterministic rules catch the intended problem.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns([0.42, 0.58], gap="medium")
    with left:
        selected_title = st.selectbox("Benchmark sample", list(sample_by_title.keys()))
        sample = sample_by_title[selected_title]
        st.markdown(
            f"""
            <div class="benchmark-card">
              <div class="small-label">{html.escape(sample.category)}</div>
              <div class="panel-title">{html.escape(sample.title)}</div>
              <div class="muted-note">{html.escape(sample.why_it_matters)}</div>
              <div class="verdict-meta">
                <div>Expected:<span>{html.escape(sample.expected_verdict)}</span></div>
                <div>Findings:<span>{len(sample.expected_findings)}</span></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("Synthetic sample text"):
            st.code(sample.paper_text.strip(), language="markdown")
        if st.button("Run Benchmark Sample", type="primary", use_container_width=True):
            comparison = run_benchmark_sample(sample.id)
            save_benchmark_result(comparison)
            save_report(comparison.report, sample.paper_text, run_kind="benchmark", benchmark_result=comparison)
            st.rerun()

    with right:
        benchmark_result = active_benchmark_result()
        if benchmark_result and benchmark_result.sample.id == sample.id:
            render_benchmark_result(benchmark_result)
        else:
            st.markdown(
                """
                <div class="empty-detail">Choose a synthetic case and run the benchmark to compare expected vs actual verdicts, findings, and claim gaps.</div>
                """,
                unsafe_allow_html=True,
            )


def render_benchmark_result(result) -> None:
    expected = result.sample
    status_class = "" if result.passed else "review"
    actual_findings = sorted({finding.type for finding in result.report.findings})
    actual_gaps = sorted({gap for claim in result.report.claims for gap in claim.gaps})
    st.markdown(
        f"""
        <div class="benchmark-grid">
          <div class="benchmark-card">
            <div class="small-label">Expected Verdict</div>
            <div class="verdict-stamp {html.escape(expected.expected_verdict.lower())}">{html.escape(expected.expected_verdict)}</div>
            <ul class="comparison-list">
              {''.join(f'<li>{html.escape(item)}</li>' for item in expected.expected_findings) or '<li>No findings expected</li>'}
            </ul>
          </div>
          <div class="benchmark-card">
            <div class="small-label">Actual Verdict</div>
            <div class="verdict-stamp {html.escape(result.report.verdict.lower())}">{html.escape(result.report.verdict)}</div>
            <div style="margin-top:.75rem;"><span class="match-pill {status_class}">{'Expected Match' if result.passed else 'Needs Review'}</span> <span class="muted-note">Benchmark match {result.score:.0%}</span></div>
          </div>
        </div>
        <div class="wide-detail-card">
          <div class="detail-title">Expected vs Actual</div>
          <div class="detail-subtitle">Benchmark match means the checker produced the expected result for this synthetic case. It does not mean the paper verdict is a pass.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    comparison_cards = [
        ("Matched Findings", result.matched_findings),
        ("Missed Findings", result.missed_findings),
        ("Extra Findings", result.extra_findings),
        ("Matched Claim Gaps", result.matched_claim_gaps),
        ("Missed Claim Gaps", result.missed_claim_gaps),
        ("Extra Claim Gaps", result.extra_claim_gaps),
    ]
    for first, second in zip(comparison_cards[::2], comparison_cards[1::2]):
        left, right = st.columns(2)
        with left:
            render_benchmark_comparison_card(first[0], first[1])
        with right:
            render_benchmark_comparison_card(second[0], second[1])
    st.markdown(
        f"""
        <div class="benchmark-grid">
          <div class="benchmark-card">
            <div class="panel-title">Actual Finding Types</div>
            <ul class="comparison-list">{''.join(f'<li>{html.escape(item)}</li>' for item in actual_findings) or '<li>none</li>'}</ul>
          </div>
          <div class="benchmark-card">
            <div class="panel-title">Actual Claim Gaps</div>
            <ul class="comparison-list">{''.join(f'<li>{html.escape(item)}</li>' for item in actual_gaps) or '<li>none</li>'}</ul>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    json_col, markdown_col = st.columns(2)
    json_col.download_button(
        "Export Benchmark JSON",
        data=result.to_json(),
        file_name=f"{safe_stem(result.sample.id)}-benchmark.json",
        mime="application/json",
        use_container_width=True,
    )
    markdown_col.download_button(
        "Export Benchmark Markdown",
        data=result.to_markdown(),
        file_name=f"{safe_stem(result.sample.id)}-benchmark.md",
        mime="text/markdown",
        use_container_width=True,
    )


def render_benchmark_comparison_card(title: str, items) -> None:
    st.markdown(
        f"""
        <div class="audit-card">
          <strong>{html.escape(title)}</strong>
          <ul class="comparison-list">{''.join(f'<li>{html.escape(item)}</li>' for item in items) or '<li>none</li>'}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workspace_page() -> None:
    summaries = list_saved_runs()
    active_run_id = st.session_state.get("workspace_run_id") or report_store().get("workspace_run_id")
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">Saved Workspace</div>
          <div class="detail-subtitle">Local run history for reloadable reports, reviewer notes, exports, and side-by-side comparisons.</div>
        </div>
        <div class="workspace-privacy">
          Reports auto-save to <strong>{html.escape(str(workspace_runs_dir()))}</strong>. The workspace stores report JSON, source anchors, snippets, and notes, but not the uploaded paper file or any API keys. If this folder is inside OneDrive or another synced directory, those local report files may sync through that service.
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not summaries:
        st.markdown(
            """
            <div class="empty-detail">No saved runs yet. Analyze a paper, built-in sample, or benchmark case and it will appear here automatically.</div>
            """,
            unsafe_allow_html=True,
        )
        return

    left, right = st.columns([0.36, 0.64], gap="medium")
    with left:
        render_saved_run_list(summaries, active_run_id)
    with right:
        selected_summary = render_saved_run_controls(summaries)
        if selected_summary:
            render_workspace_compare(summaries)


def render_saved_run_list(summaries, active_run_id: str | None) -> None:
    st.markdown('<div class="panel-title">Saved Runs</div>', unsafe_allow_html=True)
    for summary in summaries[:12]:
        active_class = " active" if summary.run_id == active_run_id else ""
        notes_label = "Notes saved" if summary.notes.strip() else "No notes"
        st.markdown(
            f"""
            <div class="workspace-card{active_class}">
              <div class="small-label">{html.escape(summary.run_kind.title())} | {html.escape(format_review_status(summary.review_status))}</div>
              <div class="panel-title">{html.escape(summary.source_name)}</div>
              <div class="source-ref">{html.escape(summary.verdict)} | Confidence {summary.confidence:.0%}</div>
              <div class="workspace-meta">
                <div><strong>{summary.claim_count}</strong>claims</div>
                <div><strong>{summary.finding_count}</strong>findings</div>
                <div><strong>{summary.evidence_score:.2f}</strong>evidence</div>
                <div><strong>{html.escape(summary.saved_at[:10])}</strong>{html.escape(notes_label)}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    if len(summaries) > 12:
        st.markdown(
            f'<div class="muted-note">{len(summaries) - 12} older runs are still available in the selector.</div>',
            unsafe_allow_html=True,
        )


def render_saved_run_controls(summaries):
    labels = {workspace_run_label(summary): summary.run_id for summary in summaries}
    selected_label = st.selectbox("Saved run", list(labels.keys()), key="workspace_saved_run")
    selected_run = load_saved_run(labels[selected_label])
    summary = selected_run.summary
    st.markdown(
        f"""
        <div class="workspace-card active">
          <div class="small-label">{html.escape(summary.run_kind.title())}</div>
          <div class="detail-title">{html.escape(summary.source_name)}</div>
          <div class="verdict-meta">
            <div>Verdict:<span>{html.escape(summary.verdict)}</span></div>
            <div>Confidence:<span>{summary.confidence:.0%}</span></div>
            <div>Claims:<span>{summary.claim_count}</span></div>
            <div>Findings:<span>{summary.finding_count}</span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if selected_run.benchmark_metadata:
        benchmark = selected_run.benchmark_metadata
        st.markdown(
            f"""
            <div class="audit-card">
              <strong>Benchmark metadata</strong>
              <div class="muted-note">{html.escape(benchmark.get("title", ""))} | Expected {html.escape(benchmark.get("expected_verdict", ""))} | Match {float(benchmark.get("score", 0.0)):.0%}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    status_options = list(REVIEW_STATUSES)
    current_status = selected_run.review_status if selected_run.review_status in status_options else status_options[0]
    status = st.selectbox(
        "Review status",
        status_options,
        index=status_options.index(current_status),
        format_func=format_review_status,
        key=f"workspace_status_{selected_run.run_id}",
    )
    notes = st.text_area(
        "Reviewer notes",
        value=selected_run.notes,
        height=120,
        key=f"workspace_notes_{selected_run.run_id}",
    )

    open_col, save_col, delete_col = st.columns(3)
    if open_col.button("Open Saved Run", type="primary", use_container_width=True):
        open_saved_run(selected_run)
        st.rerun()
    if save_col.button("Save Review Notes", use_container_width=True):
        update_saved_run_notes(selected_run.run_id, notes, status)
        st.success("Review notes saved.")
        st.rerun()
    if delete_col.button("Delete Saved Run", use_container_width=True):
        delete_saved_run(selected_run.run_id)
        if st.session_state.get("workspace_run_id") == selected_run.run_id:
            st.session_state.pop("workspace_run_id", None)
            report_store().pop("workspace_run_id", None)
        st.rerun()

    render_exports(selected_run.report)
    return summary


def render_workspace_compare(summaries) -> None:
    st.markdown(
        """
        <div class="wide-detail-card">
          <div class="detail-title">Compare Saved Runs</div>
          <div class="detail-subtitle">Pick two saved reports to compare verdict, evidence, claim volume, and finding types.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if len(summaries) < 2:
        st.markdown('<div class="empty-detail">Save at least two runs to enable comparison.</div>', unsafe_allow_html=True)
        return
    labels = {workspace_run_label(summary): summary.run_id for summary in summaries}
    label_list = list(labels.keys())
    compare_left, compare_right = st.columns(2)
    left_label = compare_left.selectbox("Compare A", label_list, key="workspace_compare_a")
    right_label = compare_right.selectbox(
        "Compare B",
        label_list,
        index=1 if len(label_list) > 1 else 0,
        key="workspace_compare_b",
    )
    if labels[left_label] == labels[right_label]:
        st.markdown('<div class="muted-note">Choose two different saved runs to compare differences.</div>', unsafe_allow_html=True)
        return
    left_run = load_saved_run(labels[left_label])
    right_run = load_saved_run(labels[right_label])
    render_run_comparison(left_run, right_run)


def render_run_comparison(left_run, right_run) -> None:
    left = left_run.report
    right = right_run.report
    rows = [
        ("Verdict", left.verdict, right.verdict),
        ("Confidence", f"{left.confidence:.0%}", f"{right.confidence:.0%}"),
        ("Evidence score", f"{left.evidence.score:.2f}", f"{right.evidence.score:.2f}"),
        ("Claims", str(len(left.claims)), str(len(right.claims))),
        ("Findings", str(len(left.findings)), str(len(right.findings))),
        ("High severity", str(left.high_severity_findings), str(right.high_severity_findings)),
    ]
    table_rows = "".join(
        f"<tr><td>{html.escape(label)}</td><td>{html.escape(left_value)}</td><td>{html.escape(right_value)}</td></tr>"
        for label, left_value, right_value in rows
    )
    left_types = sorted({finding.type for finding in left.findings})
    right_types = sorted({finding.type for finding in right.findings})
    left_only = sorted(set(left_types) - set(right_types))
    right_only = sorted(set(right_types) - set(left_types))
    shared = sorted(set(left_types) & set(right_types))
    st.markdown(
        f"""
        <table class="compare-table">
          <thead><tr><th>Metric</th><th>{html.escape(left.source_name)}</th><th>{html.escape(right.source_name)}</th></tr></thead>
          <tbody>{table_rows}</tbody>
        </table>
        <div class="benchmark-grid">
          <div class="benchmark-card">
            <div class="panel-title">Shared Finding Types</div>
            <ul class="comparison-list">{''.join(f'<li>{html.escape(item)}</li>' for item in shared) or '<li>none</li>'}</ul>
          </div>
          <div class="benchmark-card">
            <div class="panel-title">Finding Type Differences</div>
            <ul class="comparison-list">
              <li>{html.escape(left.source_name)} only: {html.escape(', '.join(left_only) or 'none')}</li>
              <li>{html.escape(right.source_name)} only: {html.escape(', '.join(right_only) or 'none')}</li>
            </ul>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_refinement_page(report) -> None:
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">Optional Refinement Chamber</div>
          <div class="detail-subtitle">Source: {html.escape(report.source_name)}. The non-AI report stays first; this page only runs if you provide session keys.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="refinement-lock">
          <div class="panel-title">Session Keys</div>
          <div class="muted-note">Keys are used for this Streamlit session and are not written to project files by The Gauntlet.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    key_col, model_col = st.columns([0.45, 0.55], gap="medium")
    with model_col:
        st.markdown('<div class="panel-title">Model Roles</div>', unsafe_allow_html=True)
        critic_provider = st.selectbox(
            "Critic provider",
            list(PROVIDER_ORDER),
            index=provider_index(DEFAULT_CRITIC_PROVIDER),
            help="First model: reads the deterministic issue brief and proposes a repair plan.",
        )
        critic_model = st.text_input(
            "Critic model",
            value=DEFAULT_PROVIDER_MODELS[critic_provider],
            key=f"critic-model-{critic_provider}",
        )
        challenger_provider = st.selectbox(
            "Challenger provider",
            list(PROVIDER_ORDER),
            index=provider_index(DEFAULT_CHALLENGER_PROVIDER),
            help="Second model: challenges the first critique and searches for remaining weak points.",
        )
        challenger_model = st.text_input(
            "Challenger model",
            value=DEFAULT_PROVIDER_MODELS[challenger_provider],
            key=f"challenger-model-{challenger_provider}",
        )
        st.markdown(
            '<div class="muted-note">Output is critique plus repair plan. The paper is not rewritten by default.</div>',
            unsafe_allow_html=True,
        )
    with key_col:
        st.markdown('<div class="panel-title">Provider Keys</div>', unsafe_allow_html=True)
        selected_providers = ordered_unique([critic_provider, challenger_provider])
        provider_keys = {}
        for provider in selected_providers:
            provider_keys[provider] = st.text_input(
                f"{provider} API key",
                type="password",
                placeholder=f"Paste {provider} key for this session",
            )
        st.markdown(
            '<div class="muted-note">Gemini, OpenAI, and Anthropic keys are read only from this page and are never exported in reports.</div>',
            unsafe_allow_html=True,
        )

    run_clicked = st.button("Run Curtain-Up Refinement", type="primary", use_container_width=True)
    if run_clicked:
        missing_keys = [provider for provider in selected_providers if not provider_keys[provider].strip()]
        if missing_keys:
            st.error(f"Paste session key(s) for: {', '.join(missing_keys)}.")
        elif not active_source_text().strip():
            st.error("Run a fresh paper analysis first so the refinement chamber has the source text.")
        else:
            try:
                with st.spinner(
                    f"Running {critic_provider} critique, {challenger_provider} challenge, and deterministic re-check..."
                ):
                    refinement_report = run_provider_refinement(
                        report,
                        active_source_text(),
                        critic=ProviderSelection(
                            role="critic",
                            provider=critic_provider,
                            model=critic_model,
                            api_key=provider_keys[critic_provider],
                        ),
                        challenger=ProviderSelection(
                            role="challenger",
                            provider=challenger_provider,
                            model=challenger_model,
                            api_key=provider_keys[challenger_provider],
                        ),
                    )
                save_refinement(refinement_report)
                st.rerun()
            except RefinementError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Refinement failed: {exc}")

    refinement_report = active_refinement()
    if refinement_report:
        render_refinement_report(refinement_report)
    else:
        st.markdown(
            """
            <div class="empty-detail">Run refinement to see the visible prompts, model critiques, disagreements, repair plan, and deterministic re-check.</div>
            """,
            unsafe_allow_html=True,
        )


def render_refinement_report(refinement_report) -> None:
    st.markdown(
        f"""
        <div class="verdict-panel">
          <div class="verdict-label">Refinement Re-Check</div>
          <div class="verdict-hero">
            <div class="verdict-stamp {html.escape(refinement_report.recheck_report.verdict.lower())}">{html.escape(refinement_report.recheck_report.verdict)}</div>
            <div>
              <div class="verdict-copy">{html.escape(refinement_report.recheck_report.summary)}</div>
              <div class="verdict-meta">
                <div>Original:<span>{html.escape(refinement_report.deterministic_verdict)}</span></div>
                <div>Disagreements:<span>{len(refinement_report.disagreements)}</span></div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    events = []
    for event in refinement_report.audit_events:
        events.append(
            f"""
            <div class="audit-card">
              <strong>{html.escape(event.step.title())}</strong>
              <div class="muted-note">{html.escape(event.status)} - {html.escape(event.detail)}</div>
            </div>
            """
        )
    st.markdown(f'<div class="audit-grid">{"".join(events)}</div>', unsafe_allow_html=True)

    st.markdown('<div class="wide-detail-card"><div class="detail-title">Visible Model Transcript</div><div class="detail-subtitle">Prompts and returned messages only. Hidden model reasoning is not requested or displayed.</div></div>', unsafe_allow_html=True)
    for turn in refinement_report.turns:
        role = turn.role.title()
        st.markdown(
            f"""
            <div class="turn-card">
              <strong>{html.escape(role)}: {html.escape(turn.provider)} | {html.escape(turn.model)}</strong>
              <div class="muted-note">Status: {html.escape(turn.status)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander(f"{role} {turn.provider} prompt"):
            st.code(turn.prompt, language="markdown")
        with st.expander(f"{role} {turn.provider} response", expanded=True):
            st.markdown(f'<div class="transcript-box">{html.escape(turn.response)}</div>', unsafe_allow_html=True)

    disagreements = "".join(f"<li>{html.escape(item)}</li>" for item in refinement_report.disagreements)
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">Disagreements And Remaining Tension</div>
          <ul class="mini-list">{disagreements or '<li>No explicit disagreements were extracted.</li>'}</ul>
        </div>
        <div class="wide-detail-card">
          <div class="detail-title">Repair Plan</div>
          <div class="transcript-box">{html.escape(refinement_report.repair_plan)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    json_col, markdown_col = st.columns(2)
    json_col.download_button(
        "Export Refinement JSON",
        data=refinement_report.to_json(),
        file_name=f"{safe_stem(refinement_report.source_name)}-gauntlet-refinement.json",
        mime="application/json",
        use_container_width=True,
    )
    markdown_col.download_button(
        "Export Refinement Markdown",
        data=refinement_report.to_markdown(),
        file_name=f"{safe_stem(refinement_report.source_name)}-gauntlet-refinement.md",
        mime="text/markdown",
        use_container_width=True,
    )


def render_flagged_panel(report) -> None:
    findings = report.findings if report else []
    high = sum(1 for finding in findings if finding.severity == "high")
    medium = sum(1 for finding in findings if finding.severity == "medium")
    low = sum(1 for finding in findings if finding.severity == "low")
    with st.container(border=True):
        st.markdown('<div class="panel-title">Flagged Problems</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="filter-row">
              <span class="filter-pill active">All&nbsp;&nbsp;{len(findings)}</span>
              <span class="filter-pill high">High&nbsp;&nbsp;{high}</span>
              <span class="filter-pill medium">Medium&nbsp;&nbsp;{medium}</span>
              <span class="filter-pill">Low&nbsp;&nbsp;{low}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not report:
            st.markdown(
                """
                <div class="finding-card low">
                  <div class="finding-title">No analysis yet <span class="severity-pill low">Ready</span></div>
                  <div class="finding-body">Upload a paper and press Analyze Paper to fill this rail with human-readable findings.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif findings:
            for finding in findings:
                render_finding(finding)
        else:
            st.markdown(
                """
                <div class="finding-card low">
                  <div class="finding-title">No internal contradictions <span class="severity-pill low">Low</span></div>
                  <div class="finding-body">The v2 rule set did not find direct internal conflicts in this paper.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_finding(finding) -> None:
    severity = html.escape(finding.severity)
    related = ""
    if finding.related_sentence:
        related = f"<p><strong>Related:</strong> {html.escape(finding.related_sentence)}</p>"
    claim_link = f" | Claim: {html.escape(finding.claim_id)}" if finding.claim_id else ""
    trigger = f" | Trigger: {html.escape(finding.trigger)}" if finding.trigger else ""
    st.markdown(
        f"""
        <div class="finding-card {severity}">
          <div class="finding-title">{html.escape(finding.id or finding.type)} - {html.escape(finding.type)} <span class="severity-pill {severity}">{severity.title()}</span></div>
          <div class="finding-meta">Section: {html.escape(finding.section)} | Severity: {severity} | Confidence: {finding.confidence:.0%}{claim_link}{trigger}</div>
          <div class="finding-body">
            <p>{html.escape(finding.sentence)}</p>
            <div class="source-ref">{html.escape(source_reference(finding.source_span))}</div>
            {related}
            <p><strong>Why it matters:</strong> {html.escape(finding.explanation)}</p>
            <p><strong>Repair:</strong> {html.escape(finding.repair_suggestion)}</p>
            <span class="repair-button-look">Repair Suggestion</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_source_expander(f"Source for {finding.id or finding.type}", finding.source_span, related_span=finding.related_source_span)


def render_source_expander(label: str, source_span, evidence_links=None, related_span=None) -> None:
    if not source_span and not related_span and not evidence_links:
        return
    with st.expander(label):
        if source_span:
            render_source_span_block("Primary source", source_span)
        if related_span:
            render_source_span_block("Related source", related_span)
        if evidence_links:
            st.markdown("**Linked evidence**")
            for link in evidence_links:
                render_source_span_block(f"{link.id} - {link.type.title()}", link.source_span)


def render_source_span_block(title: str, span) -> None:
    if not span:
        st.markdown(f'<div class="muted-note">{html.escape(title)}: source unavailable</div>', unsafe_allow_html=True)
        return
    source_html = (
        '<div class="source-snippet">'
        f"<strong>{html.escape(title)}</strong>"
        f'<div class="muted-note">{html.escape(source_reference(span))}</div>'
        f"<div>{html.escape(span.text)}</div>"
        "</div>"
    )
    st.markdown(source_html, unsafe_allow_html=True)


def render_source_trace(report, limit: int = 12) -> None:
    if not getattr(report, "source_spans", None):
        return
    visible_spans = report.source_spans[:limit]
    cards = []
    for span in visible_spans:
        cards.append(
            '<div class="audit-card">'
            f"<strong>{html.escape(span.anchor_id)}</strong>"
            f'<div class="muted-note">{html.escape(source_reference(span))}</div>'
            f'<div class="claim-text">{html.escape(span.text)}</div>'
            "</div>"
        )
    remaining = len(report.source_spans) - len(visible_spans)
    remaining_note = (
        f'<div class="muted-note">{remaining} more source anchors are included in JSON and Markdown exports.</div>'
        if remaining > 0
        else ""
    )
    trace_html = (
        '<div class="wide-detail-card">'
        '<div class="detail-title">Source Trace</div>'
        '<div class="detail-subtitle">Exact sentence anchors used by the local rule audit. '
        "Page numbers are shown when the loader can recover them.</div>"
        "</div>"
        f'<div class="audit-grid">{"".join(cards)}</div>'
        f"{remaining_note}"
    )
    st.markdown(trace_html, unsafe_allow_html=True)


def safe_stem(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0]
    cleaned = "".join(character if character.isalnum() or character in "-_" else "-" for character in stem)
    return cleaned.strip("-") or "paper"


def workspace_run_label(summary) -> str:
    date = summary.saved_at[:19].replace("T", " ") if summary.saved_at else "unknown date"
    return f"{summary.source_name} | {summary.verdict} | {date} | {summary.run_id[-8:]}"


def format_review_status(status: str) -> str:
    labels = {
        "unreviewed": "Unreviewed",
        "confirmed": "Confirmed",
        "false-positive": "False Positive",
        "needs-follow-up": "Needs Follow-Up",
    }
    return labels.get(status, status.replace("-", " ").title())


def provider_index(provider: str) -> int:
    try:
        return list(PROVIDER_ORDER).index(provider)
    except ValueError:
        return 0


def ordered_unique(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def evidence_label(score: float) -> str:
    if score >= 0.7:
        return "Strong"
    if score >= 0.45:
        return "Adequate"
    if score >= 0.25:
        return "Weak"
    return "Thin"


def render_footer(report) -> None:
    status = "Analysis complete" if report else "Ready for paper upload"
    source = report.source_name if report else "No document loaded"
    st.markdown(
        f"""
        <div class="footer-status">
          <div>{html.escape(status)}</div>
          <div>Rules Engine: v3.0.0&nbsp;&nbsp;&nbsp; Rule Set: Theory/Paradox&nbsp;&nbsp;&nbsp; Benchmarks: Synthetic Demo Corpus</div>
          <div>{html.escape(source)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
