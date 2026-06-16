from __future__ import annotations

import html
from dataclasses import replace
from urllib.parse import quote

import streamlit as st

from gauntlet_core import analyze_loaded_document, analyze_paper_text
from gauntlet_core.batch import (
    BatchScanItem,
    batch_items_to_csv,
    build_demo_batch_items,
    build_batch_report_bundle,
    failed_batch_item,
    filter_batch_items,
    sort_batch_items,
    summarize_report,
)
from gauntlet_core.benchmarks import list_benchmark_samples, run_benchmark_sample, run_calibration_suite
from gauntlet_core.document_loader import SUPPORTED_EXTENSIONS, load_document_from_bytes
from gauntlet_core.evidence_map import build_claim_evidence_map, claim_evidence_map_to_markdown
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
from gauntlet_core.repair_workshop import (
    REPAIR_STATUSES,
    build_repair_steps,
    repair_status_counts,
    repair_status_label,
    repair_workshop_to_markdown,
)
from gauntlet_core.reviewer_packet import (
    build_reviewer_packet_bundle,
    reviewer_packet_to_html,
    reviewer_packet_to_markdown,
)
from gauntlet_core.revision_recheck import (
    recheck_repair_revision,
    revision_recheck_log_to_markdown,
    revision_status_label,
)
from gauntlet_core.sample_text import SAMPLE_PAPER
from gauntlet_core.share import (
    build_demo_share_pack,
    build_demo_share_summary,
    build_share_card_html,
    build_share_card_svg,
    build_x_post,
)
from gauntlet_core.source_reader import build_source_reader_view, source_reader_to_markdown
from gauntlet_core.source_review import build_source_review_items, source_review_to_markdown
from gauntlet_core.system_check import collect_system_check
from gauntlet_core.workspace import (
    ISSUE_REVIEW_STATUSES,
    REVIEW_STATUSES,
    delete_saved_run,
    list_saved_runs,
    load_saved_run,
    save_analysis_run,
    update_saved_run_revision_recheck,
    update_saved_run_repair_progress,
    update_saved_run_issue_review,
    update_saved_run_notes,
    workspace_runs_dir,
)


st.set_page_config(page_title="The Gauntlet", page_icon="G", layout="wide")

VALID_PAGES = (
    "summary",
    "workspace",
    "batch",
    "share",
    "system",
    "action",
    "source",
    "breakdown",
    "benchmarks",
    "claims",
    "contradictions",
    "evidence",
    "refinement",
)
PAGE_LABELS = {
    "summary": "Summary",
    "workspace": "Workspace",
    "batch": "Batch",
    "share": "Share Demo",
    "system": "System Check",
    "action": "Repair Workshop",
    "source": "Source Reader",
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
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
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
.evidence-map-card {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: white;
  padding: .9rem;
  margin-bottom: .75rem;
  box-shadow: 0 10px 24px rgba(22, 34, 44, .05);
}
.evidence-map-card.high {
  border-left: 4px solid var(--gauntlet-red);
}
.evidence-map-card.medium {
  border-left: 4px solid var(--gauntlet-amber);
}
.evidence-map-card.low {
  border-left: 4px solid var(--gauntlet-teal);
}
.coverage-pill {
  display: inline-block;
  border-radius: 6px;
  padding: .18rem .5rem;
  font-size: .75rem;
  font-weight: 850;
  background: #e6f6f3;
  color: var(--gauntlet-teal);
}
.coverage-pill.missing,
.coverage-pill.weak {
  background: var(--gauntlet-red-bg);
  color: var(--gauntlet-red);
}
.coverage-pill.linked {
  background: var(--gauntlet-amber-bg);
  color: var(--gauntlet-amber);
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
.start-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: .7rem;
  margin-top: .85rem;
}
.start-step {
  min-height: 112px;
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  padding: .8rem;
  background: #f9fbfa;
}
.start-step strong {
  display: block;
  color: var(--gauntlet-ink);
  font-size: .9rem;
  margin-bottom: .35rem;
}
.start-step span {
  color: var(--gauntlet-muted);
  font-size: .82rem;
  line-height: 1.35;
}
.source-snippet {
  border-left: 3px solid var(--gauntlet-teal);
  background: #fbfcfd;
  color: #273340;
  padding: .6rem .75rem;
  margin: .45rem 0;
}
.source-jump {
  display: inline-block;
  border: 1px solid #c7e2df;
  border-radius: 6px;
  background: #effaf8;
  color: var(--gauntlet-teal) !important;
  font-size: .76rem;
  font-weight: 850;
  padding: .22rem .48rem;
  margin-top: .45rem;
  text-decoration: none !important;
}
.source-viewer-grid {
  display: grid;
  grid-template-columns: minmax(260px, .32fr) minmax(0, .68fr);
  gap: .9rem;
}
.source-lens {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: white;
  padding: 1rem;
  box-shadow: var(--gauntlet-shadow);
}
.source-context-line {
  border-left: 3px solid var(--gauntlet-border);
  background: #fbfcfd;
  color: #394653;
  padding: .75rem .85rem;
  margin: .55rem 0;
  line-height: 1.55;
}
.source-context-line.active {
  border-left-color: var(--gauntlet-teal);
  background: #effaf8;
  color: #132f2c;
  font-weight: 720;
}
.source-anchor-list {
  max-height: 520px;
  overflow: auto;
  padding-right: .25rem;
}
.source-issue-list {
  max-height: 440px;
  overflow: auto;
  padding-right: .25rem;
  margin-bottom: .8rem;
}
.source-issue-card {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: white;
  padding: .78rem;
  margin-bottom: .58rem;
  box-shadow: var(--gauntlet-shadow);
}
.source-issue-card.active {
  border-color: var(--gauntlet-teal);
  background: #effaf8;
}
.source-issue-card.high {
  border-left: 4px solid var(--gauntlet-danger);
}
.source-issue-card.medium {
  border-left: 4px solid var(--gauntlet-gold);
}
.source-issue-card.low {
  border-left: 4px solid var(--gauntlet-teal);
}
.source-reader-toolbar {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: white;
  padding: .85rem;
  margin-bottom: .85rem;
  box-shadow: 0 10px 24px rgba(22, 34, 44, .05);
}
.source-reader-result {
  border: 1px solid var(--gauntlet-border);
  border-radius: 8px;
  background: white;
  padding: .72rem .78rem;
  margin-bottom: .55rem;
}
.source-reader-result.active {
  border-color: var(--gauntlet-teal);
  background: #effaf8;
}
.source-reader-selected {
  border: 1px solid #9fd3cf;
  border-radius: 8px;
  background: #f7fffd;
  color: #183d39;
  padding: 1rem;
  margin-bottom: .75rem;
  box-shadow: var(--gauntlet-shadow);
  line-height: 1.65;
}
.source-reader-selected strong {
  display: block;
  color: var(--gauntlet-teal);
  margin-bottom: .35rem;
}
.source-reader-related {
  border-left: 4px solid var(--gauntlet-teal);
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
  .batch-grid,
  .source-viewer-grid,
  .detail-grid,
  .start-grid,
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
    elif page == "batch":
        render_batch_page()
    elif page == "share":
        render_share_demo_page()
    elif page == "system":
        render_system_check_page()
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


def active_calibration_result():
    if "calibration_result" in st.session_state:
        return st.session_state["calibration_result"]
    return report_store().get("calibration_result")


def active_batch_items() -> list[BatchScanItem]:
    if "batch_items" in st.session_state:
        return st.session_state["batch_items"]
    return report_store().get("batch_items", [])


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


def run_sample_analysis() -> None:
    report = analyze_paper_text(SAMPLE_PAPER, source_name="sample-paper.txt")
    save_report(report, SAMPLE_PAPER, run_kind="sample")


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


def save_calibration_result(calibration_result) -> None:
    st.session_state["calibration_result"] = calibration_result
    report_store()["calibration_result"] = calibration_result


def save_batch_items(items: list[BatchScanItem]) -> None:
    st.session_state["batch_items"] = items
    report_store()["batch_items"] = items


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
                    run_sample_analysis()
                    st.rerun()
                    return
                elif upload is not None:
                    loaded_document = load_document_from_bytes(upload.name, upload.getvalue())
                    paper_text = loaded_document.text
                    if not paper_text.strip():
                        render_upload_error(
                            "No readable text was found in that file.",
                            "The parser opened the file, but extraction returned no text. Try exporting the paper as text, checking whether the PDF is scanned images, or running System Check.",
                        )
                        return
                    report = analyze_loaded_document(loaded_document)
                else:
                    st.error("Upload a paper or turn on the sample paper first.")
                    return
            except Exception as exc:  # Streamlit should show clean user-facing errors.
                render_upload_error("The Gauntlet could not read that file.", str(exc))
                return
            save_report(report, paper_text, run_kind=run_kind)
            st.rerun()

        st.markdown(
            '<p class="local-note">Analysis is 100% local. Completed reports auto-save under .gauntlet/workspace/runs/ without saving the uploaded file.</p>',
            unsafe_allow_html=True,
        )


def render_upload_error(message: str, detail: str = "") -> None:
    st.error(message)
    st.markdown(
        """
        <div class="empty-detail">
          Open <a href="?page=system" target="_self">System Check</a> to verify Python, dependencies, workspace access, and launcher logs before retrying.
        </div>
        """,
        unsafe_allow_html=True,
    )
    if detail:
        with st.expander("Troubleshooting detail"):
            st.code(detail, language="text")


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
        """,
        unsafe_allow_html=True,
    )
    render_start_here_panel()
    st.markdown(
        """
        <div class="stat-strip">
          <div class="stat-tile"><div class="stat-title">Claims Made</div><div class="stat-number">-</div><div class="stat-note">Waiting for analysis</div></div>
          <div class="stat-tile"><div class="stat-title">Supported Claims</div><div class="stat-number">-</div><div class="stat-note">Local rules only</div></div>
          <div class="stat-tile"><div class="stat-title">Internal Contradictions</div><div class="stat-number">-</div><div class="stat-note">No paper loaded</div></div>
          <div class="stat-tile"><div class="stat-title">Evidence Quality</div><div class="stat-number">-</div><div class="stat-note">0 to 1 score</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_start_here_panel() -> None:
    with st.container(border=True):
        st.markdown(
            """
            <div class="panel-title">Start Here</div>
            <div class="muted-note">The fastest first run is the built-in sample. After that, upload a real paper and follow the audit trail from verdict to source snippets and exports.</div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Try Sample Paper", type="primary", use_container_width=True):
            run_sample_analysis()
            st.rerun()
        st.markdown(
            """
            <div class="start-grid">
              <div class="start-step"><strong>1. Try sample</strong><span>Run the demo paper to confirm the local checker and workspace are working.</span></div>
              <div class="start-step"><strong>2. Upload paper</strong><span>Use PDF, DOCX, TXT, or MD. The normal checker does not need an API key.</span></div>
              <div class="start-step"><strong>3. Inspect issues</strong><span>Open Breakdown, Source Reader, Repair Workshop, and Evidence to trace every finding.</span></div>
              <div class="start-step"><strong>4. Export packet</strong><span>Use Workspace to export JSON, Markdown, HTML, report bundles, or reviewer packets.</span></div>
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
    render_document_quality_panel(report)
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
    elif page == "action":
        render_action_plan_page(report)
    elif page == "source":
        render_source_viewer_page(report)
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
    render_document_quality_panel(report, always=True)
    render_stat_strip(report)
    render_breakdowns(report)
    render_curtain_up(report)
    render_claims_page(report, compact=True)
    render_contradictions_page(report, compact=True)
    render_evidence_page(report, compact=True)
    render_action_plan_page(report, compact=True)
    render_exports(report)


def render_document_quality_panel(report, always: bool = False) -> None:
    quality = getattr(report, "document_quality", None)
    if not quality or quality.status == "unknown":
        return
    if quality.status == "ok" and not always:
        return
    issue_rows = "".join(
        f"<li><strong>{html.escape(issue.type)}</strong> ({html.escape(issue.severity)}): {html.escape(issue.message)}</li>"
        for issue in quality.issues
    ) or "<li>No extraction-quality issues were detected.</li>"
    recovery_rows = "".join(
        f"<li>{html.escape(issue.recovery)}</li>"
        for issue in quality.issues
        if issue.recovery
    ) or "<li>No recovery action needed.</li>"
    status_note = {
        "ok": "The extracted text looks usable for the deterministic audit.",
        "warn": "Review the source text before treating the verdict as final.",
        "fail": "The verdict may be unfair because extraction quality is poor.",
    }.get(quality.status, "Extraction quality was checked.")
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="small-label">Document Extraction Quality</div>
          <div class="detail-title">{html.escape(quality.status.upper())} | {quality.score:.2f}/1.00</div>
          <div class="detail-subtitle">{html.escape(status_note)}</div>
          <div class="verdict-meta">
            <div>Words:<span>{quality.word_count}</span></div>
            <div>Sentences:<span>{quality.sentence_count}</span></div>
            <div>Anchors:<span>{quality.source_span_count}</span></div>
          </div>
          <div class="breakdown-grid" style="margin-top:.8rem;">
            <div>
              <div class="small-label">Issues</div>
              <ul class="comparison-list">{issue_rows}</ul>
            </div>
            <div>
              <div class="small-label">Recovery</div>
              <ul class="comparison-list">{recovery_rows}</ul>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
              {source_view_link(link.source_span)}
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
          {source_view_link(claim.source_span)}
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
    evidence_map = build_claim_evidence_map(report)
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
    render_claim_evidence_map(report, evidence_map, compact=compact)
    if report.evidence.evidence_links:
        for link in report.evidence.evidence_links:
            st.markdown(
                f"""
                <div class="evidence-link-card">
                  <strong>{html.escape(link.id)} - {html.escape(link.type.title())}</strong>
                  <div class="muted-note">{html.escape(link.section)} | Sentence {link.sentence_index} | Confidence {link.confidence:.0%}</div>
                  <div class="source-ref">{html.escape(source_reference(link.source_span))}</div>
                  {source_view_link(link.source_span)}
                  <div class="claim-text">{html.escape(link.snippet)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            render_source_expander(f"Source for {link.id}", link.source_span)
    if not compact:
        render_source_trace(report, limit=18)


def render_claim_evidence_map(report, evidence_map, compact: bool = False) -> None:
    rows = evidence_map.rows[:4] if compact else evidence_map.rows
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">Claim-Evidence Map</div>
          <div class="detail-subtitle">Every detected claim is matched against the evidence snippets The Gauntlet linked to it. Missing and weak links are repair targets.</div>
        </div>
        <div class="stat-strip">
          <div class="stat-tile"><div class="stat-title">Claims</div><div class="stat-number">{len(evidence_map.rows)}</div><div class="stat-note">Detected claims</div></div>
          <div class="stat-tile"><div class="stat-title">With Evidence</div><div class="stat-number">{evidence_map.claims_with_evidence}</div><div class="stat-note">Any linked snippet</div></div>
          <div class="stat-tile"><div class="stat-title">Usable Links</div><div class="stat-number">{evidence_map.claims_with_usable_evidence}</div><div class="stat-note">Confidence 42%+</div></div>
          <div class="stat-tile"><div class="stat-title">Orphan Evidence</div><div class="stat-number">{len(evidence_map.orphan_evidence_links)}</div><div class="stat-note">Evidence not tied to a claim</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not evidence_map.rows:
        st.markdown(
            '<div class="empty-detail">No clear claims were detected, so no claim-evidence map was generated.</div>',
            unsafe_allow_html=True,
        )
        return
    cards = []
    for row in rows:
        links = ", ".join(link.id for link in row.evidence_links) if row.evidence_links else "none"
        gaps = ", ".join(row.gaps) if row.gaps else "none"
        cards.append(
            f"""
            <div class="evidence-map-card {html.escape(row.priority)}">
              <div class="finding-title">
                <span>{html.escape(row.claim_id)} - {html.escape(row.claim_status.title())}</span>
                <span class="coverage-pill {html.escape(row.coverage)}">{html.escape(row.coverage.upper())}</span>
              </div>
              <div class="finding-meta">Evidence strength {row.evidence_strength:.2f} | Links: {html.escape(links)} | Gaps: {html.escape(gaps)}</div>
              <div class="finding-body">{html.escape(row.claim)}</div>
              <div class="source-ref">{html.escape(source_reference(row.source_span))}</div>
              {source_view_link(row.source_span, label="Open Claim Source")}
              <p><strong>Repair:</strong> {html.escape(row.repair_suggestion)}</p>
            </div>
            """
        )
    remaining = len(evidence_map.rows) - len(rows)
    remaining_note = f'<div class="muted-note">{remaining} more claim-evidence rows are included in the export.</div>' if remaining > 0 else ""
    st.markdown(f'<div class="audit-grid">{"".join(cards)}</div>{remaining_note}', unsafe_allow_html=True)
    if not compact:
        st.download_button(
            "Export Claim-Evidence Map",
            data=claim_evidence_map_to_markdown(report, evidence_map),
            file_name=f"{safe_stem(report.source_name)}-claim-evidence-map.md",
            mime="text/markdown",
            use_container_width=True,
        )
        render_orphan_evidence(evidence_map)


def render_orphan_evidence(evidence_map) -> None:
    if not evidence_map.orphan_evidence_links:
        return
    cards = []
    for link in evidence_map.orphan_evidence_links[:8]:
        cards.append(
            f"""
            <div class="evidence-link-card">
              <strong>{html.escape(link.id)} - Orphan {html.escape(link.type.title())}</strong>
              <div class="muted-note">Confidence {link.confidence:.0%}. This snippet was detected as evidence but was not linked to a specific claim.</div>
              <div class="source-ref">{html.escape(source_reference(link.source_span))}</div>
              {source_view_link(link.source_span)}
              <div class="claim-text">{html.escape(link.snippet)}</div>
            </div>
            """
        )
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">Orphan Evidence</div>
          <div class="detail-subtitle">Evidence-like snippets that may need to be moved closer to the claim they support.</div>
        </div>
        <div class="audit-grid">{''.join(cards)}</div>
        """,
        unsafe_allow_html=True,
    )


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
    json_col, markdown_col, html_col, bundle_col = st.columns(4)
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
    html_col.download_button(
        "Export HTML Report",
        data=report.to_html(),
        file_name=f"{safe_stem(report.source_name)}-gauntlet-report.html",
        mime="text/html",
        use_container_width=True,
    )
    bundle_col.download_button(
        "Export Report Bundle",
        data=report.to_bundle_bytes(),
        file_name=f"{safe_stem(report.source_name)}-gauntlet-report-bundle.zip",
        mime="application/zip",
        use_container_width=True,
    )


def render_reviewer_packet_exports(saved_run) -> None:
    report = saved_run.report
    stem = safe_stem(report.source_name)
    st.markdown(
        """
        <div class="wide-detail-card">
          <div class="detail-title">Reviewer Packet</div>
          <div class="detail-subtitle">Export a shareable packet with verdict, claim-evidence map, issue reviews, repair progress, source snippets, and revision re-check summaries.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    markdown_col, html_col, bundle_col = st.columns(3)
    markdown_col.download_button(
        "Export Reviewer Packet Markdown",
        data=reviewer_packet_to_markdown(
            report,
            issue_reviews=saved_run.issue_reviews,
            repair_progress=saved_run.repair_progress,
            revision_rechecks=saved_run.revision_rechecks,
        ),
        file_name=f"{stem}-reviewer-packet.md",
        mime="text/markdown",
        use_container_width=True,
    )
    html_col.download_button(
        "Export Reviewer Packet HTML",
        data=reviewer_packet_to_html(
            report,
            issue_reviews=saved_run.issue_reviews,
            repair_progress=saved_run.repair_progress,
            revision_rechecks=saved_run.revision_rechecks,
        ),
        file_name=f"{stem}-reviewer-packet.html",
        mime="text/html",
        use_container_width=True,
    )
    bundle_col.download_button(
        "Export Reviewer Packet ZIP",
        data=build_reviewer_packet_bundle(
            report,
            issue_reviews=saved_run.issue_reviews,
            repair_progress=saved_run.repair_progress,
            revision_rechecks=saved_run.revision_rechecks,
        ),
        file_name=f"{stem}-reviewer-packet.zip",
        mime="application/zip",
        use_container_width=True,
    )
    st.markdown(
        '<div class="muted-note">Reviewer packets use saved report data, source anchors, snippets, reviewer notes, repair progress, and revision snippets only. They do not include the full uploaded paper or API keys.</div>',
        unsafe_allow_html=True,
    )


def render_action_plan_page(report, compact: bool = False) -> None:
    run_id = st.session_state.get("workspace_run_id") or report_store().get("workspace_run_id")
    saved_run = load_workspace_run_safely(run_id)
    saved_progress = saved_run.repair_progress if saved_run else {}
    saved_rechecks = saved_run.revision_rechecks if saved_run else {}
    steps = build_repair_steps(report, saved_progress)
    if compact:
        steps = steps[:6]
    title = "Repair Workshop" if not compact else "Top Repair Steps"
    subtitle = (
        "Work through deterministic repair steps, save local progress, and export a reviewer-ready checklist."
        if not compact
        else "The highest-value repairs before exporting or refining the paper."
    )
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">{title}</div>
          <div class="detail-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not steps:
        st.markdown('<div class="empty-detail">No repair steps were generated.</div>', unsafe_allow_html=True)
        return

    counts = repair_status_counts(steps)
    high = sum(1 for step in steps if step.priority == "high")
    in_progress = counts.get("in-progress", 0)
    fixed = counts.get("fixed", 0)
    remaining = counts.get("todo", 0)
    st.markdown(
        f"""
        <div class="stat-strip">
          <div class="stat-tile"><div class="stat-title">Steps</div><div class="stat-number">{len(steps)}</div><div class="stat-note">Repair items</div></div>
          <div class="stat-tile"><div class="stat-title">To Do</div><div class="stat-number">{remaining}</div><div class="stat-note">Still open</div></div>
          <div class="stat-tile"><div class="stat-title">In Progress</div><div class="stat-number">{in_progress}</div><div class="stat-note">Being repaired</div></div>
          <div class="stat-tile"><div class="stat-title">Fixed</div><div class="stat-number">{fixed}</div><div class="stat-note">Marked done</div></div>
          <div class="stat-tile"><div class="stat-title">Re-Checks</div><div class="stat-number">{len(saved_rechecks)}</div><div class="stat-note">Revision tests</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if compact:
        step_cards = "".join(repair_step_card_html(step, include_progress=False) for step in steps)
        st.markdown(f'<div class="audit-grid">{step_cards}</div>', unsafe_allow_html=True)
        st.markdown(
            '<a class="export-chip" href="?page=action" target="_self">Open full Repair Workshop</a>',
            unsafe_allow_html=True,
        )
        return

    if not run_id:
        st.markdown(
            '<div class="workspace-privacy">Repair progress saves to the local workspace after an analysis run is saved. This report is currently open without a workspace run id, so progress controls can still export but cannot save yet.</div>',
            unsafe_allow_html=True,
        )

    filter_choice = st.radio(
        "Repair filter",
        ("All", "High Priority", "Needs Repair", "In Progress", "Fixed", "False Positive"),
        horizontal=True,
    )
    visible_steps = filter_repair_steps(steps, filter_choice)
    if not visible_steps:
        st.markdown('<div class="empty-detail">No repair steps match this filter.</div>', unsafe_allow_html=True)

    for step in visible_steps:
        with st.container(border=True):
            st.markdown(repair_step_card_html(step), unsafe_allow_html=True)
            status_key = f"repair_status_{step.id}"
            note_key = f"repair_note_{step.id}"
            revision_key = f"repair_revision_{step.id}"
            left, right = st.columns([0.28, 0.72])
            left.selectbox(
                "Repair status",
                list(REPAIR_STATUSES),
                index=list(REPAIR_STATUSES).index(step.status),
                format_func=repair_status_label,
                key=status_key,
            )
            right.text_area(
                "Reviewer note",
                value=step.reviewer_note,
                height=86,
                key=note_key,
            )
            st.text_area(
                "Revision to test",
                value=(saved_rechecks.get(step.id, {}) or {}).get("revised_text", ""),
                height=110,
                key=revision_key,
                help="Paste the revised sentence or paragraph for this repair step. The checker re-runs deterministic rules on this snippet only.",
            )
            test_col, result_col = st.columns([0.28, 0.72])
            if test_col.button("Test Revision", use_container_width=True, key=f"test_revision_{step.id}"):
                revision_text = st.session_state.get(revision_key, "")
                result = recheck_repair_revision(report, step, revision_text)
                if run_id:
                    update_saved_run_revision_recheck(run_id, result)
                    st.success("Revision re-check saved locally.")
                    st.rerun()
                else:
                    st.session_state[f"revision_result_{step.id}"] = result.to_dict()
            result = (saved_rechecks or {}).get(step.id)
            result = result or st.session_state.get(f"revision_result_{step.id}")
            if result:
                result_col.markdown(revision_result_card_html(result, step.source_span), unsafe_allow_html=True)

    save_col, export_col = st.columns(2)
    if save_col.button("Save Repair Progress", type="primary", use_container_width=True, disabled=not bool(run_id)):
        for step in steps:
            update_saved_run_repair_progress(
                run_id,
                step.id,
                st.session_state.get(f"repair_status_{step.id}", step.status),
                st.session_state.get(f"repair_note_{step.id}", step.reviewer_note),
            )
        st.success("Repair progress saved locally.")
        st.rerun()
    export_col.download_button(
        "Export Repair Workshop Markdown",
        data=repair_workshop_to_markdown(report, collect_repair_steps_from_state(steps)),
        file_name=f"{safe_stem(report.source_name)}-repair-workshop.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.download_button(
        "Export Revision Re-Check Log",
        data=revision_recheck_log_to_markdown(report, load_revision_rechecks(run_id)),
        file_name=f"{safe_stem(report.source_name)}-revision-recheck-log.md",
        mime="text/markdown",
        use_container_width=True,
    )


def load_workspace_run_safely(run_id: str | None):
    if not run_id:
        return None
    try:
        return load_saved_run(run_id)
    except (OSError, ValueError, KeyError):
        return None


def load_repair_progress(run_id: str | None) -> dict:
    saved_run = load_workspace_run_safely(run_id)
    return saved_run.repair_progress if saved_run else {}


def load_revision_rechecks(run_id: str | None) -> dict:
    saved_run = load_workspace_run_safely(run_id)
    return saved_run.revision_rechecks if saved_run else {}


def filter_repair_steps(steps, filter_choice: str):
    if filter_choice == "High Priority":
        return [step for step in steps if step.priority == "high"]
    if filter_choice == "Needs Repair":
        return [step for step in steps if step.status in {"todo", "in-progress"}]
    if filter_choice == "In Progress":
        return [step for step in steps if step.status == "in-progress"]
    if filter_choice == "Fixed":
        return [step for step in steps if step.status == "fixed"]
    if filter_choice == "False Positive":
        return [step for step in steps if step.status == "false-positive"]
    return steps


def collect_repair_steps_from_state(steps):
    collected = []
    for step in steps:
        collected.append(
            replace(
                step,
                status=st.session_state.get(f"repair_status_{step.id}", step.status),
                reviewer_note=st.session_state.get(f"repair_note_{step.id}", step.reviewer_note),
            )
        )
    return collected


def repair_step_card_html(step, include_progress: bool = True) -> str:
    progress = ""
    if include_progress:
        progress = f'<div class="source-ref">Status: {html.escape(repair_status_label(step.status))}</div>'
        if step.reviewer_note.strip():
            progress += f'<div class="muted-note">Note: {html.escape(truncate_text(step.reviewer_note, 180))}</div>'
    return f"""
    <div class="finding-card {html.escape(step.priority)}">
      <div class="finding-title">
        <span>{html.escape(step.id)} - {html.escape(step.title)}</span>
        <span class="severity-pill {html.escape(step.priority)}">{html.escape(step.priority.upper())}</span>
      </div>
      <div class="finding-meta">{html.escape(step.category)} | Target: {html.escape(step.target)}</div>
      <div class="finding-body">{html.escape(step.body)}</div>
      <p><strong>Rule explanation:</strong> {html.escape(step.explanation)}</p>
      <div class="repair-button-look">{html.escape(step.suggested_fix)}</div>
      <div class="source-ref">{html.escape(source_reference(step.source_span))}</div>
      {progress}
      {source_view_link(step.source_span, label="Open in Source Reader")}
    </div>
    """


def revision_result_card_html(result: dict, source_span=None) -> str:
    status = str(result.get("status", "still-weak"))
    source_link = source_view_link(source_span, label="Open in Source Reader")
    return f"""
    <div class="audit-card">
      <strong>Revision Re-Check: {html.escape(revision_status_label(status))}</strong>
      <div class="muted-note">Claim {html.escape(str(result.get("original_claim_status", "none")))} -> {html.escape(str(result.get("revised_claim_status", "none")))} | Gaps {int(result.get("original_gap_count", 0))} -> {int(result.get("revised_gap_count", 0))}</div>
      <div class="claim-text">{html.escape(truncate_text(str(result.get("summary", "")), 260))}</div>
      <div class="source-ref">Checked: {html.escape(str(result.get("checked_at", "")))}</div>
      {source_link}
    </div>
    """


def render_batch_page() -> None:
    st.markdown(
        """
        <div class="wide-detail-card">
          <div class="detail-title">Batch Scan</div>
          <div class="detail-subtitle">Upload several papers, run the local checker once, then export a CSV summary or a ZIP bundle with per-paper reports.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([0.34, 0.66], gap="medium")
    with left:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Batch Input</div>', unsafe_allow_html=True)
            uploads = st.file_uploader(
                "Choose papers",
                type=[extension.lstrip(".") for extension in sorted(SUPPORTED_EXTENSIONS)],
                accept_multiple_files=True,
                help="Select multiple PDF, DOCX, TXT, or MD papers.",
            )
            uploaded_count = len(uploads or [])
            st.markdown(
                f"""
                <div class="document-card">
                  <div class="small-label">Batch privacy</div>
                  <div class="doc-row"><span>Selected</span><strong>{uploaded_count}</strong></div>
                  <div class="doc-row"><span>Saved</span><strong>Reports only</strong></div>
                  <div class="doc-row"><span>AI</span><strong>Not used</strong></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            run_clicked = st.button(
                "Run Batch Scan",
                type="primary",
                use_container_width=True,
                disabled=not uploads,
            )
            if run_clicked:
                run_batch_uploads(uploads)
                st.rerun()
            if st.button(
                "Load Demo Batch",
                use_container_width=True,
                help="Run the synthetic benchmark papers as a ready-made batch scan.",
            ):
                run_demo_batch()
                st.rerun()
            st.markdown(
                '<p class="local-note">Batch scan runs on local deterministic rules. The demo batch uses synthetic benchmark papers. Workspace saves report JSON/snippets, not full paper files.</p>',
                unsafe_allow_html=True,
            )

    with right:
        items = active_batch_items()
        if items:
            render_batch_results(items)
        else:
            st.markdown(
                """
                <div class="empty-detail">Select two or more papers, or load the synthetic demo batch, to create a verdict table with confidence, evidence score, claim count, finding count, and top risk types.</div>
                """,
                unsafe_allow_html=True,
            )


def run_batch_uploads(uploads) -> None:
    items: list[BatchScanItem] = []
    progress = st.progress(0, text="Starting batch scan...")
    for index, upload in enumerate(uploads, start=1):
        progress.progress((index - 1) / max(1, len(uploads)), text=f"Analyzing {upload.name}...")
        try:
            loaded_document = load_document_from_bytes(upload.name, upload.getvalue())
            if not loaded_document.text.strip():
                raise ValueError("No readable text was found in that file.")
            report = analyze_loaded_document(loaded_document)
            try:
                save_analysis_run(report, run_kind="batch")
            except OSError as exc:
                st.warning(f"{upload.name} analyzed, but the workspace could not save it: {exc}")
            items.append(summarize_report(report))
        except Exception as exc:
            items.append(failed_batch_item(upload.name, str(exc)))
    progress.progress(1.0, text="Batch scan complete.")
    save_batch_items(items)


def run_demo_batch() -> None:
    items = build_demo_batch_items()
    for item in items:
        if not item.report:
            continue
        try:
            save_analysis_run(item.report, run_kind="demo-batch")
        except OSError as exc:
            st.warning(f"{item.source_name} analyzed, but the workspace could not save it: {exc}")
    save_batch_items(items)


def render_batch_results(items: list[BatchScanItem]) -> None:
    visible_items = render_batch_filter_controls(items)
    analyzed = sum(1 for item in visible_items if item.status == "analyzed")
    failed = sum(1 for item in visible_items if item.status == "failed")
    high_risk = sum(1 for item in visible_items if item.high_severity_findings > 0 or item.verdict == "CREATES_NEW_PARADOXES")
    avg_evidence = (
        sum(item.evidence_score for item in visible_items if item.status == "analyzed") / analyzed if analyzed else 0
    )
    st.markdown(
        f"""
        <div class="stat-strip">
          <div class="stat-tile"><div class="stat-title">Showing</div><div class="stat-number">{len(visible_items)}</div><div class="stat-note">of {len(items)} scanned papers</div></div>
          <div class="stat-tile"><div class="stat-title">High Risk</div><div class="stat-number">{high_risk}</div><div class="stat-note">New paradoxes or high severity</div></div>
          <div class="stat-tile"><div class="stat-title">Avg Evidence</div><div class="stat-number">{avg_evidence:.2f}</div><div class="stat-note">Analyzed papers only</div></div>
          <div class="stat-tile"><div class="stat-title">Status</div><div class="stat-number">{failed}</div><div class="stat-note">failed to parse</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not visible_items:
        st.markdown('<div class="empty-detail">No papers match the current filters.</div>', unsafe_allow_html=True)
        return

    rows = [batch_row_for_display(item) for item in visible_items]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    csv_col, zip_col = st.columns(2)
    csv_col.download_button(
        "Export Filtered CSV",
        data=batch_items_to_csv(visible_items),
        file_name="gauntlet-batch-summary.csv",
        mime="text/csv",
        use_container_width=True,
    )
    zip_col.download_button(
        "Export Filtered Bundle",
        data=build_batch_report_bundle(visible_items),
        file_name="gauntlet-batch-report-bundle.zip",
        mime="application/zip",
        use_container_width=True,
    )

    completed = [item for item in visible_items if item.report]
    if completed:
        labels = {
            f"{item.source_name} | {item.verdict} | {item.confidence:.0%}": index
            for index, item in enumerate(completed)
        }
        selected_label = st.selectbox("Open batch report", list(labels.keys()))
        if st.button("Open Selected Batch Report", use_container_width=True):
            selected = completed[labels[selected_label]]
            st.session_state["report"] = selected.report
            st.session_state["paper_text"] = ""
            report_store()["report"] = selected.report
            report_store()["paper_text"] = ""
            st.query_params["page"] = "breakdown"
            st.rerun()


def render_batch_filter_controls(items: list[BatchScanItem]) -> list[BatchScanItem]:
    st.markdown(
        """
        <div class="wide-detail-card">
          <div class="detail-title">Filter & Sort</div>
          <div class="detail-subtitle">Focus the batch table before exporting the CSV or bundle.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    verdict_options = ["RESOLVES", "PARTIAL", "FAILS", "CREATES_NEW_PARADOXES", "PARSE_FAILED"]
    present_verdicts = [
        verdict
        for verdict in verdict_options
        if any((item.verdict if item.status == "analyzed" else "PARSE_FAILED") == verdict for item in items)
    ]
    filter_col, risk_col, sort_col = st.columns([0.42, 0.24, 0.34])
    selected_verdicts = filter_col.multiselect(
        "Verdicts",
        verdict_options,
        default=present_verdicts or verdict_options,
    )
    high_risk_only = risk_col.checkbox("High risk only")
    weak_evidence_only = risk_col.checkbox("Weak evidence only")
    sort_by = sort_col.selectbox(
        "Sort by",
        ["Highest risk", "Most findings", "Lowest evidence", "Highest confidence", "Lowest confidence", "Verdict", "Filename"],
    )

    filtered = filter_batch_items(
        items,
        verdicts=set(selected_verdicts) if selected_verdicts else set(),
        high_risk_only=high_risk_only,
        weak_evidence_only=weak_evidence_only,
    )
    return sort_batch_items(filtered, sort_by)


def batch_row_for_display(item: BatchScanItem) -> dict[str, str | int]:
    return {
        "File": item.source_name,
        "Status": item.status,
        "Verdict": item.verdict or "-",
        "Confidence": f"{item.confidence:.0%}" if item.status == "analyzed" else "-",
        "Evidence": f"{item.evidence_score:.2f}" if item.status == "analyzed" else "-",
        "Claims": item.claim_count if item.status == "analyzed" else 0,
        "Findings": item.finding_count if item.status == "analyzed" else 0,
        "Top Risks": "; ".join(item.top_findings) or item.error or "-",
    }


def render_share_demo_page() -> None:
    summary = build_demo_share_summary()
    x_post = build_x_post()
    st.markdown(
        """
        <div class="wide-detail-card">
          <div class="detail-title">Share Demo Kit</div>
          <div class="detail-subtitle">Generate a public demo pack for X: post copy, screenshot-ready cards, demo batch summaries, and the full offline batch bundle.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="stat-strip">
          <div class="stat-tile"><div class="stat-title">Demo Papers</div><div class="stat-number">{summary.paper_count}</div><div class="stat-note">synthetic benchmark cases</div></div>
          <div class="stat-tile"><div class="stat-title">Analyzed</div><div class="stat-number">{summary.analyzed_count}</div><div class="stat-note">local deterministic reports</div></div>
          <div class="stat-tile"><div class="stat-title">High Risk</div><div class="stat-number">{summary.high_risk_count}</div><div class="stat-note">fails, paradoxes, or severe findings</div></div>
          <div class="stat-tile"><div class="stat-title">Avg Evidence</div><div class="stat-number">{summary.avg_evidence:.2f}</div><div class="stat-note">demo batch evidence score</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([0.48, 0.52], gap="medium")
    with left:
        with st.container(border=True):
            st.markdown('<div class="panel-title">X Post Draft</div>', unsafe_allow_html=True)
            st.code(x_post, language="text")
            st.download_button(
                "Download X Post",
                data=x_post,
                file_name="gauntlet-x-post.txt",
                mime="text/plain",
                use_container_width=True,
            )
        st.download_button(
            "Download Demo Share Pack",
            data=build_demo_share_pack(),
            file_name="gauntlet-demo-share-pack.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )
        st.markdown(
            '<p class="local-note">The share pack uses synthetic benchmark papers only. It does not include private uploaded documents, API keys, or model output.</p>',
            unsafe_allow_html=True,
        )

    with right:
        findings = ", ".join(summary.top_findings) or "No top findings"
        st.markdown(
            f"""
            <div class="wide-detail-card">
              <div class="small-label">Card Preview</div>
              <div class="detail-title">Local Non-AI Paper Checker</div>
              <div class="detail-subtitle">Transparent verdicts for claims, evidence, contradictions, source anchors, benchmarks, and batch exports.</div>
              <div class="muted-note">Demo catches: {html.escape(findings)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        card_col, svg_col = st.columns(2)
        card_col.download_button(
            "Download Share Card HTML",
            data=build_share_card_html(summary),
            file_name="gauntlet-share-card.html",
            mime="text/html",
            use_container_width=True,
        )
        svg_col.download_button(
            "Download Share Card SVG",
            data=build_share_card_svg(summary),
            file_name="gauntlet-share-card.svg",
            mime="image/svg+xml",
            use_container_width=True,
        )


def render_system_check_page() -> None:
    report = collect_system_check(workspace_path=workspace_runs_dir())
    counts = report.status_counts
    status_label = report.overall_status.upper()
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="small-label">System Check</div>
          <div class="detail-title">Local Diagnostics</div>
          <div class="detail-subtitle">A quick health check for the GitHub ZIP launcher, dependencies, workspace, and logs. This diagnostic does not include uploaded papers, report contents, API keys, or full launcher logs.</div>
          <div class="verdict-meta">
            <div>Status:<span>{html.escape(status_label)}</span></div>
            <div>Checks:<span>{len(report.items)}</span></div>
            <div>Generated:<span>{html.escape(report.generated_at)}</span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="stat-strip">
          <div class="stat-tile"><div class="stat-title">Overall</div><div class="stat-number">{html.escape(status_label)}</div><div class="stat-note">Current diagnostic state</div></div>
          <div class="stat-tile"><div class="stat-title">OK</div><div class="stat-number">{counts.get("ok", 0)}</div><div class="stat-note">Ready checks</div></div>
          <div class="stat-tile"><div class="stat-title">Warnings</div><div class="stat-number">{counts.get("warn", 0)}</div><div class="stat-note">Review if stuck</div></div>
          <div class="stat-tile"><div class="stat-title">Failures</div><div class="stat-number">{counts.get("fail", 0)}</div><div class="stat-note">Needs fixing</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    runtime_col, export_col = st.columns([0.52, 0.48], gap="medium")
    with runtime_col:
        st.markdown(
            f"""
            <div class="wide-detail-card">
              <div class="panel-title">Runtime</div>
              <div class="doc-row"><span>App version</span><strong>{html.escape(report.app_version)}</strong></div>
              <div class="doc-row"><span>Python</span><strong>{html.escape(report.python_version)}</strong></div>
              <div class="doc-row"><span>Repo</span><strong>{html.escape(report.repo_path)}</strong></div>
              <div class="doc-row"><span>Workspace</span><strong>{html.escape(report.workspace_path)}</strong></div>
              <div class="doc-row"><span>Launcher log</span><strong>{html.escape(report.launcher_log_path)}</strong></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with export_col:
        st.markdown(
            """
            <div class="wide-detail-card">
              <div class="panel-title">Diagnostics Export</div>
              <div class="muted-note">Use this when opening a GitHub issue. It contains setup status and local paths only, not private paper text.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        json_col, markdown_col = st.columns(2)
        json_col.download_button(
            "Download Diagnostics JSON",
            data=report.to_json(),
            file_name="gauntlet-system-check.json",
            mime="application/json",
            use_container_width=True,
        )
        markdown_col.download_button(
            "Download Diagnostics Markdown",
            data=report.to_markdown(),
            file_name="gauntlet-system-check.md",
            mime="text/markdown",
            use_container_width=True,
        )

    st.markdown('<div class="panel-title">Checks</div>', unsafe_allow_html=True)
    for item in report.items:
        severity_class = "low" if item.status == "ok" else "medium" if item.status == "warn" else "high"
        st.markdown(
            f"""
            <div class="finding-card {severity_class}">
              <div class="finding-title">
                <span>{html.escape(item.name)}</span>
                <span class="severity-pill {severity_class}">{html.escape(item.status.upper())}</span>
              </div>
              <div class="finding-body">{html.escape(item.detail)}</div>
              {f'<div class="repair-button-look">{html.escape(item.recovery)}</div>' if item.recovery else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.text_area("Copy diagnostics", value=report.to_markdown(), height=380)


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
    render_calibration_dashboard()
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


def render_calibration_dashboard() -> None:
    result = active_calibration_result()
    st.markdown(
        """
        <div class="wide-detail-card">
          <div class="small-label">Calibration Dashboard</div>
          <div class="detail-title">Analyzer Trust Check</div>
          <div class="detail-subtitle">Run every synthetic theory/paradox benchmark at once, including false-positive guardrails. These fixtures calibrate rule behavior; they are not a claim of real-world accuracy.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    run_col, note_col = st.columns([0.32, 0.68], gap="medium")
    with run_col:
        if st.button("Run Full Calibration Suite", type="primary", use_container_width=True):
            with st.spinner("Running synthetic calibration suite..."):
                save_calibration_result(run_calibration_suite())
            st.rerun()
    with note_col:
        st.markdown(
            """
            <div class="empty-detail">The full suite checks verdict matches, missed findings, extra findings, missed/extra claim gaps, and unwanted false-positive guardrail hits.</div>
            """,
            unsafe_allow_html=True,
        )

    if not result:
        return

    failing_cases = ", ".join(f"`{sample_id}`" for sample_id in result.failing_sample_ids) or "none"
    if result.gate:
        gate_status = "PASS" if result.gate.passed else "FAIL"
    else:
        gate_status = "NOT COMPUTED"
    gate_thresholds = (
        f"overall >= {result.gate.overall_threshold:.0%}, guardrail >= {result.gate.guardrail_threshold:.0%}"
        if result.gate
        else "overall >= 90%, guardrail >= 95%"
    )
    gate_rates = (
        f"overall {result.gate.overall_pass:.0%}, guardrail {result.gate.guardrail_pass:.0%}"
        if result.gate
        else f"overall {result.pass_rate:.0%}, guardrail {result.guardrail_pass_rate:.0%}"
    )
    gate_failures = ", ".join(result.gate.failures) if result.gate and result.gate.failures else "none"
    gate_warnings = ", ".join(result.gate.warnings) if result.gate and result.gate.warnings else "none"

    st.markdown(
        f"""
        <div class="benchmark-grid">
          <div class="benchmark-card">
            <div class="small-label">Last Run Status</div>
            <div class="muted-note">Threshold status: {html.escape(gate_status)}</div>
            <ul class="comparison-list">
              <li>Thresholds: {html.escape(gate_thresholds)}</li>
              <li>Observed rates: {html.escape(gate_rates)}</li>
              <li>Version: {html.escape(result.calibration_version)}</li>
            </ul>
          </div>
          <div class="benchmark-card">
            <div class="small-label">Overall Pass Rate</div>
            <div class="stat-number">{result.pass_rate:.0%}</div>
            <div class="muted-note">{result.passed_count}/{result.sample_count} synthetic cases matched expectations.</div>
          </div>
          <div class="benchmark-card">
            <div class="small-label">Verdict Match</div>
            <div class="stat-number">{result.verdict_match_rate:.0%}</div>
            <div class="muted-note">{result.verdict_match_count}/{result.sample_count} verdicts matched the expected outcome.</div>
          </div>
          <div class="benchmark-card">
            <div class="small-label">Guardrail Pass</div>
            <div class="stat-number">{result.guardrail_pass_rate:.0%}</div>
            <div class="muted-note">{result.guardrail_failure_count} false-positive guardrail failures across {result.guardrail_check_count} checks.</div>
          </div>
          <div class="benchmark-card">
            <div class="small-label">Failing Cases</div>
            <div class="stat-number">{len(result.failing_sample_ids)}</div>
            <div class="muted-note">{html.escape(failing_cases)}</div>
          </div>
          <div class="benchmark-card">
            <div class="small-label">Gate Issues</div>
            <div class="muted-note">Failures: {html.escape(gate_failures)}</div>
            <div class="muted-note">Warnings: {html.escape(gate_warnings)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    category_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(summary.category)}</td>"
            f"<td>{summary.passed_count}/{summary.sample_count}</td>"
            f"<td>{summary.pass_rate:.0%}</td>"
            f"<td>{summary.verdict_match_rate:.0%}</td>"
            f"<td>{summary.guardrail_pass_rate:.0%}</td>"
            f"<td>{html.escape(', '.join(summary.failing_sample_ids) or 'none')}</td>"
            f"<td>{html.escape(summary.confidence_explanation or 'No failures in this category.')}</td>"
            "</tr>"
        )
        for summary in result.category_summaries
    )
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="panel-title">Category Calibration</div>
          <table class="compare-table">
            <thead><tr><th>Category</th><th>Passed</th><th>Pass Rate</th><th>Verdict Match</th><th>Guardrail Pass</th><th>Failing Cases</th><th>Confidence / Rule Explanation</th></tr></thead>
            <tbody>{category_rows}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )
    failed_results = [item for item in result.results if not item.passed]
    if failed_results:
        st.markdown('<div class="panel-title">Failing Cases</div>', unsafe_allow_html=True)
        for item in failed_results:
            st.markdown(
                f"""
                <div class="audit-card">
                  <strong>{html.escape(item.sample.title)}</strong>
                  <div class="muted-note">Expected {html.escape(item.sample.expected_verdict)}; actual {html.escape(item.report.verdict)}. Missed findings: {html.escape(', '.join(item.missed_findings) or 'none')}. Extra findings: {html.escape(', '.join(item.extra_findings) or 'none')}.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div class="empty-detail">No failing calibration cases in the latest run.</div>',
            unsafe_allow_html=True,
        )

    json_col, markdown_col = st.columns(2)
    json_col.download_button(
        "Export Calibration JSON",
        data=result.to_json(),
        file_name="gauntlet-calibration-suite.json",
        mime="application/json",
        use_container_width=True,
    )
    markdown_col.download_button(
        "Export Calibration Markdown",
        data=result.to_markdown(),
        file_name="gauntlet-calibration-suite.md",
        mime="text/markdown",
        use_container_width=True,
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
        ("Guarded Findings Kept Out", result.absent_findings_kept_out),
        ("Unexpected Guarded Findings", result.unexpected_absent_findings),
        ("Guarded Claim Gaps Kept Out", result.absent_claim_gaps_kept_out),
        ("Unexpected Guarded Claim Gaps", result.unexpected_absent_claim_gaps),
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


SOURCE_REVIEW_FILTERS = ("All", "Findings", "Claims", "Evidence", "High Risk", "Needs Repair")


def render_source_viewer_page(report) -> None:
    source_spans = list(getattr(report, "source_spans", []) or [])
    review_items = build_source_review_items(report)
    run_id = st.session_state.get("workspace_run_id") or report_store().get("workspace_run_id")
    saved_run = load_workspace_run_safely(run_id)
    saved_progress = saved_run.repair_progress if saved_run else {}
    saved_rechecks = saved_run.revision_rechecks if saved_run else {}
    saved_issue_reviews = saved_run.issue_reviews if saved_run else {}
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">Source Reader</div>
          <div class="detail-subtitle">Source: {html.escape(report.source_name)}. Search extracted source anchors, jump from problems to the exact sentence, and inspect linked audit items without saving the full paper.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not source_spans:
        st.markdown(
            '<div class="empty-detail">This report does not contain source anchors. Run a fresh analysis to rebuild the source trace.</div>',
            unsafe_allow_html=True,
        )
        return

    section_options = ["All"] + sorted({span.section or "Document" for span in source_spans})
    page_numbers = sorted({span.page_number for span in source_spans if span.page_number is not None})
    page_options = ["All"] + [str(page) for page in page_numbers]
    left, center, right = st.columns([0.27, 0.43, 0.30], gap="medium")
    with left:
        st.markdown('<div class="panel-title">Reader Controls</div>', unsafe_allow_html=True)
        query = st.text_input(
            "Search source",
            value="",
            placeholder="Search anchors, snippets, pages, or sections",
        )
        selected_section = st.selectbox("Section", section_options)
        selected_page = st.selectbox("Page", page_options)
        view = build_source_reader_view(
            report,
            selected_anchor=current_source_anchor(),
            query=query,
            filters={
                "section": selected_section,
                "page": selected_page,
                "repair_progress": saved_progress,
                "revision_rechecks": saved_rechecks,
            },
        )
        render_source_reader_results(view)

        st.markdown('<div class="panel-title">Issue Queue</div>', unsafe_allow_html=True)
        selected_filter = st.radio(
            "Issue filter",
            SOURCE_REVIEW_FILTERS,
            horizontal=True,
            label_visibility="collapsed",
        )
        visible_items = filter_source_review_items(review_items, selected_filter)
        render_source_review_issue_queue(visible_items, view.selected_anchor, saved_issue_reviews)
        st.download_button(
            "Export Source Review Markdown",
            data=source_review_to_markdown(report, visible_items),
            file_name=f"{safe_stem(report.source_name)}-source-review.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with center:
        render_source_reader_context(view)
    with right:
        render_source_reader_linked_panel(view, run_id=run_id, issue_reviews=saved_issue_reviews)
        st.download_button(
            "Export Source Reader Markdown",
            data=source_reader_to_markdown(report, view),
            file_name=f"{safe_stem(report.source_name)}-source-reader.md",
            mime="text/markdown",
            use_container_width=True,
        )


def filter_source_review_items(items, selected_filter: str):
    if selected_filter == "Findings":
        return [item for item in items if item.kind == "Finding"]
    if selected_filter == "Claims":
        return [item for item in items if item.kind == "Claim"]
    if selected_filter == "Evidence":
        return [item for item in items if item.kind == "Evidence"]
    if selected_filter == "High Risk":
        return [item for item in items if item.severity == "high" or item.priority <= 20]
    if selected_filter == "Needs Repair":
        return [item for item in items if item.kind == "Repair" or item.status in {"failed", "partial", "weak", "needs repair"}]
    return list(items)


def render_source_review_issue_queue(items, selected_anchor: str, issue_reviews=None) -> None:
    issue_reviews = issue_reviews or {}
    if not items:
        st.markdown('<div class="empty-detail">No source review items match this filter.</div>', unsafe_allow_html=True)
        return
    cards = []
    for item in items[:80]:
        source_anchor = item.source_span.anchor_id if item.source_span else ""
        related_anchor = item.related_source_span.anchor_id if item.related_source_span else ""
        active_class = " active" if selected_anchor in {source_anchor, related_anchor} else ""
        severity_class = item.severity if item.severity in {"high", "medium", "low"} else "low"
        link = source_view_link(item.source_span, label="Open Source") if item.source_span else ""
        review = issue_reviews.get(item.id, {})
        review_status = issue_review_label(str(review.get("status", "unreviewed")))
        cards.append(
            f'<div class="source-issue-card {html.escape(severity_class)}{active_class}">'
            f'<div class="small-label">{html.escape(item.kind)} | {html.escape(item.id)}</div>'
            f'<strong>{html.escape(item.title)}</strong>'
            f'<div class="muted-note">Priority {item.priority} | {html.escape(item.severity)} | {html.escape(item.status)}</div>'
            f'<div class="source-ref">Review: {html.escape(review_status)}</div>'
            f'{link}'
            f'<div class="claim-text">{html.escape(truncate_text(item.body, 170))}</div>'
            "</div>"
        )
    remaining = len(items) - min(len(items), 80)
    remaining_note = f'<div class="muted-note">{remaining} more source review items are included in export.</div>' if remaining else ""
    st.markdown(f'<div class="source-issue-list">{"".join(cards)}</div>{remaining_note}', unsafe_allow_html=True)


def render_source_reader_results(view) -> None:
    title = "Source Results"
    if view.query:
        title = f"Source Results ({len(view.matching_anchors)})"
    st.markdown(f'<div class="panel-title">{html.escape(title)}</div>', unsafe_allow_html=True)
    if not view.matching_anchors:
        st.markdown('<div class="empty-detail">No source anchors match that search or filter.</div>', unsafe_allow_html=True)
        return
    cards = []
    for anchor in view.matching_anchors[:80]:
        active_class = " active" if anchor.anchor_id == view.selected_anchor else ""
        match_note = "match" if anchor.is_match else "available"
        linked_note = f"{anchor.related_count} linked audit items" if anchor.related_count else "no direct audit links"
        cards.append(
            f'<div class="source-reader-result{active_class}">'
            f'<div class="small-label">{html.escape(anchor.anchor_id)} | {html.escape(match_note)}</div>'
            f'<div class="muted-note">{html.escape(anchor.reference)}</div>'
            f'{source_reader_link(anchor.anchor_id, label="Open")}'
            f'<div class="source-ref">{html.escape(linked_note)}</div>'
            f'<div class="claim-text">{html.escape(truncate_text(anchor.text, 170))}</div>'
            "</div>"
        )
    remaining = len(view.matching_anchors) - min(len(view.matching_anchors), 80)
    remaining_note = f'<div class="muted-note">{remaining} more source matches are available through export/search.</div>' if remaining else ""
    st.markdown(f'<div class="source-anchor-list">{"".join(cards)}</div>{remaining_note}', unsafe_allow_html=True)


def render_source_anchor_list(source_spans, selected_anchor: str, limit: int = 80) -> None:
    visible_spans = source_spans[:limit]
    cards = []
    for span in visible_spans:
        active_class = " active" if span.anchor_id == selected_anchor else ""
        cards.append(
            f'<div class="workspace-card{active_class}">'
            f'<div class="small-label">{html.escape(span.anchor_id)}</div>'
            f'<div class="muted-note">{html.escape(source_reference(span))}</div>'
            f'{source_view_link(span, label="Open")}'
            f'<div class="claim-text">{html.escape(truncate_text(span.text, 160))}</div>'
            "</div>"
        )
    remaining = len(source_spans) - len(visible_spans)
    remaining_note = (
        f'<div class="muted-note">{remaining} more anchors are included in exports.</div>' if remaining > 0 else ""
    )
    st.markdown(
        f'<div class="source-anchor-list">{"".join(cards)}</div>{remaining_note}',
        unsafe_allow_html=True,
    )


def render_source_reader_context(view) -> None:
    if not view.selected_span:
        st.markdown('<div class="empty-detail">No selected source anchor is available.</div>', unsafe_allow_html=True)
        return
    selected_span = view.selected_span
    st.markdown(
        f"""
        <div class="source-lens">
          <div class="small-label">Selected Anchor</div>
          <div class="detail-title">{html.escape(selected_span.anchor_id)}</div>
          <div class="verdict-meta">
            <div>Page:<span>{html.escape(str(selected_span.page_number) if selected_span.page_number is not None else "n/a")}</span></div>
            <div>Section:<span>{html.escape(selected_span.section or "Document")}</span></div>
            <div>Sentence:<span>{selected_span.sentence_index}</span></div>
            <div>Chars:<span>{selected_span.char_start}-{selected_span.char_end}</span></div>
          </div>
        </div>
        <div class="wide-detail-card">
          <div class="detail-title">Reader Context</div>
          <div class="detail-subtitle">The highlighted sentence is shown with nearby extracted sentences. This is extracted text, not a stored copy of the full uploaded paper.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    lines = []
    for span in view.context_spans:
        active_class = " active" if span.anchor_id == selected_span.anchor_id else ""
        if active_class:
            lines.append(
                f'<div class="source-reader-selected">'
                f'<strong>Highlighted source sentence | {html.escape(span.anchor_id)}</strong>'
                f'<div class="muted-note">{html.escape(source_reference(span))}</div>'
                f"<div>{html.escape(span.text)}</div>"
                "</div>"
            )
            continue
        lines.append(
            f'<div class="source-context-line">'
            f"<strong>Nearby source sentence | {html.escape(span.anchor_id)}</strong>"
            f'<div class="muted-note">{html.escape(source_reference(span))}</div>'
            f"{source_reader_link(span.anchor_id, label='Open')}"
            f"<div>{html.escape(span.text)}</div>"
            "</div>"
        )
    st.markdown("".join(lines), unsafe_allow_html=True)


def render_source_reader_linked_panel(view, run_id: str | None = None, issue_reviews=None) -> None:
    issue_reviews = issue_reviews or {}
    st.markdown(
        """
        <div class="wide-detail-card">
          <div class="detail-title">Linked Audit</div>
          <div class="detail-subtitle">Claims, findings, evidence, repair steps, saved revision checks, and issue review notes attached to the selected source.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not view.related_items:
        st.markdown('<div class="empty-detail">No audit items point directly to this anchor.</div>', unsafe_allow_html=True)
        return
    cards = []
    for item in view.related_items:
        related_note = ""
        if item.related_source_span and item.related_source_span.anchor_id != view.selected_anchor:
            related_note = f'<div class="source-ref">Related: {html.escape(source_reference(item.related_source_span))}</div>'
        review = issue_reviews.get(item.id, {})
        review_status = issue_review_label(str(review.get("status", "unreviewed")))
        reviewer_note = str(review.get("reviewer_note", "")).strip()
        note_html = f'<div class="muted-note">Reviewer note: {html.escape(truncate_text(reviewer_note, 180))}</div>' if reviewer_note else ""
        cards.append(
            '<div class="audit-card source-reader-related">'
            f'<strong>{html.escape(item.kind)}: {html.escape(item.title)}</strong>'
            f'<div class="muted-note">{html.escape(item.id)} | {html.escape(item.status)}</div>'
            f'<div class="source-ref">Issue review: {html.escape(review_status)}</div>'
            f'{related_note}'
            f'{note_html}'
            f'<div class="claim-text">{html.escape(truncate_text(item.body, 260))}</div>'
            f'<p><strong>Rule explanation:</strong> {html.escape(item.explanation)}</p>'
            f'<p><strong>Repair:</strong> {html.escape(item.repair_suggestion)}</p>'
            "</div>"
        )
    st.markdown(f'<div class="audit-grid">{"".join(cards)}</div>', unsafe_allow_html=True)
    render_issue_review_controls(view.related_items, run_id, issue_reviews)


def render_issue_review_controls(items, run_id: str | None, issue_reviews) -> None:
    st.markdown(
        """
        <div class="wide-detail-card">
          <div class="detail-title">Issue Review Register</div>
          <div class="detail-subtitle">Mark linked issues as confirmed, false positive, needs repair, or resolved. Notes save locally with this workspace run.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not run_id:
        st.markdown(
            '<div class="workspace-privacy">Issue review notes save after a report is opened from or saved to the local workspace.</div>',
            unsafe_allow_html=True,
        )
        return
    visible_items = list(items[:8])
    status_options = list(ISSUE_REVIEW_STATUSES)
    for item in visible_items:
        current = issue_reviews.get(item.id, {})
        current_status = str(current.get("status", "unreviewed"))
        if current_status not in status_options:
            current_status = "unreviewed"
        st.markdown(
            f"""
            <div class="workspace-card">
              <div class="small-label">{html.escape(item.kind)} | {html.escape(item.id)}</div>
              <strong>{html.escape(item.title)}</strong>
              <div class="claim-text">{html.escape(truncate_text(item.body, 170))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        status_col, note_col = st.columns([0.36, 0.64])
        status_col.selectbox(
            "Issue review status",
            status_options,
            index=status_options.index(current_status),
            format_func=issue_review_label,
            key=f"issue_review_status_{item.id}",
        )
        note_col.text_area(
            "Issue review note",
            value=str(current.get("reviewer_note", "")),
            height=72,
            key=f"issue_review_note_{item.id}",
        )
    if len(items) > len(visible_items):
        st.markdown(
            f'<div class="muted-note">{len(items) - len(visible_items)} more linked items are visible by changing the selected source anchor.</div>',
            unsafe_allow_html=True,
        )
    if st.button("Save Issue Reviews", use_container_width=True):
        for item in visible_items:
            update_saved_run_issue_review(
                run_id,
                item.id,
                st.session_state.get(f"issue_review_status_{item.id}", "unreviewed"),
                st.session_state.get(f"issue_review_note_{item.id}", ""),
            )
        st.success("Issue reviews saved locally.")
        st.rerun()


def render_source_lens(report, selected_span, review_items=None) -> None:
    st.markdown(
        f"""
        <div class="source-lens">
          <div class="small-label">Selected Anchor</div>
          <div class="detail-title">{html.escape(selected_span.anchor_id)}</div>
          <div class="verdict-meta">
            <div>Page:<span>{html.escape(str(selected_span.page_number) if selected_span.page_number is not None else "n/a")}</span></div>
            <div>Section:<span>{html.escape(selected_span.section or "Document")}</span></div>
            <div>Sentence:<span>{selected_span.sentence_index}</span></div>
            <div>Chars:<span>{selected_span.char_start}-{selected_span.char_end}</span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_source_context(report, selected_span)
    render_source_review_issue_details(selected_span, review_items or [])
    render_related_audit_items(report, selected_span)


def render_source_context(report, selected_span) -> None:
    source_spans = list(getattr(report, "source_spans", []) or [])
    selected_index = next(
        (index for index, span in enumerate(source_spans) if span.anchor_id == selected_span.anchor_id),
        0,
    )
    context_spans = source_spans[max(0, selected_index - 2) : min(len(source_spans), selected_index + 3)]
    lines = []
    for span in context_spans:
        active_class = " active" if span.anchor_id == selected_span.anchor_id else ""
        title = "Highlighted source sentence" if active_class else "Nearby source sentence"
        lines.append(
            f'<div class="source-context-line{active_class}">'
            f"<strong>{html.escape(title)} | {html.escape(span.anchor_id)}</strong>"
            f'<div class="muted-note">{html.escape(source_reference(span))}</div>'
            f"<div>{html.escape(span.text)}</div>"
            "</div>"
        )
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">Highlighted Source</div>
          <div class="detail-subtitle">The selected sentence is shown with nearby extracted sentences for context.</div>
        </div>
        {''.join(lines)}
        """,
        unsafe_allow_html=True,
    )


def render_source_review_issue_details(selected_span, review_items) -> None:
    anchor_id = selected_span.anchor_id
    related_items = [
        item
        for item in review_items
        if same_anchor(item.source_span, anchor_id) or same_anchor(item.related_source_span, anchor_id)
    ]
    cards = []
    for item in related_items:
        related_note = ""
        if item.related_source_span and item.related_source_span.anchor_id != anchor_id:
            related_note = f'<div class="source-ref">Related: {html.escape(source_reference(item.related_source_span))}</div>'
        cards.append(
            '<div class="audit-card">'
            f'<strong>{html.escape(item.kind)}: {html.escape(item.title)}</strong>'
            f'<div class="muted-note">Priority {item.priority} | {html.escape(item.severity)} | {html.escape(item.status)}</div>'
            f'{related_note}'
            f'<div class="claim-text">{html.escape(truncate_text(item.body, 260))}</div>'
            f'<p><strong>Rule explanation:</strong> {html.escape(item.explanation)}</p>'
            f'<p><strong>Repair:</strong> {html.escape(item.repair_suggestion)}</p>'
            "</div>"
        )
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">Rule Explanation & Repair</div>
          <div class="detail-subtitle">Issue-led review items attached to this source sentence.</div>
        </div>
        <div class="audit-grid">{''.join(cards) or '<div class="empty-detail">No source review item points directly to this anchor.</div>'}</div>
        """,
        unsafe_allow_html=True,
    )


def render_related_audit_items(report, selected_span) -> None:
    related_cards = []
    anchor_id = selected_span.anchor_id
    for claim in report.claims:
        if same_anchor(claim.source_span, anchor_id):
            related_cards.append(
                audit_relation_card("Claim", claim.id or "Claim", claim.status, claim.claim)
            )
    for finding in report.findings:
        if same_anchor(finding.source_span, anchor_id):
            related_cards.append(
                audit_relation_card("Finding", finding.id or finding.type, finding.severity, finding.sentence)
            )
        if same_anchor(finding.related_source_span, anchor_id):
            related_cards.append(
                audit_relation_card("Related Finding Source", finding.id or finding.type, finding.type, finding.related_sentence or finding.sentence)
            )
    for link in report.evidence.evidence_links:
        if same_anchor(link.source_span, anchor_id):
            related_cards.append(
                audit_relation_card("Evidence", link.id, link.type, link.snippet)
            )
    st.markdown(
        f"""
        <div class="wide-detail-card">
          <div class="detail-title">Linked Audit Items</div>
          <div class="detail-subtitle">Claims, findings, and evidence snippets attached to this exact source anchor.</div>
        </div>
        <div class="audit-grid">{''.join(related_cards) or '<div class="empty-detail">No claim, finding, or evidence item points directly to this anchor.</div>'}</div>
        """,
        unsafe_allow_html=True,
    )


def audit_relation_card(kind: str, title: str, meta: str, body: str) -> str:
    return (
        '<div class="audit-card">'
        f"<strong>{html.escape(kind)}: {html.escape(title)}</strong>"
        f'<div class="muted-note">{html.escape(meta)}</div>'
        f'<div class="claim-text">{html.escape(truncate_text(body, 260))}</div>'
        "</div>"
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
        repair_label = repair_progress_summary(summary.repair_progress_counts or {})
        revision_label = revision_recheck_summary(summary.revision_recheck_counts or {})
        issue_label = issue_review_summary(summary.issue_review_counts or {})
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
              <div class="source-ref">Repair progress: {html.escape(repair_label)}</div>
              <div class="source-ref">Revision re-checks: {html.escape(revision_label)}</div>
              <div class="source-ref">Issue reviews: {html.escape(issue_label)}</div>
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
          <div class="source-ref">Repair progress: {html.escape(repair_progress_summary(summary.repair_progress_counts or {}))}</div>
          <div class="source-ref">Revision re-checks: {html.escape(revision_recheck_summary(summary.revision_recheck_counts or {}))}</div>
          <div class="source-ref">Issue reviews: {html.escape(issue_review_summary(summary.issue_review_counts or {}))}</div>
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
    render_reviewer_packet_exports(selected_run)
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
            {source_view_link(finding.source_span)}
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
        f"{source_view_link(span)}"
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
            f"{source_view_link(span)}"
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


def current_source_anchor() -> str:
    anchor = st.query_params.get("anchor", "")
    if isinstance(anchor, list):
        anchor = anchor[0] if anchor else ""
    return anchor


def source_view_link(span, label: str = "View Source") -> str:
    if not span:
        return ""
    anchor = quote(span.anchor_id, safe="")
    return f'<a class="source-jump" href="?page=source&anchor={anchor}" target="_self">{html.escape(label)}</a>'


def source_reader_link(anchor_id: str, label: str = "Open in Source Reader") -> str:
    if not anchor_id:
        return ""
    anchor = quote(anchor_id, safe="")
    return f'<a class="source-jump" href="?page=source&anchor={anchor}" target="_self">{html.escape(label)}</a>'


def source_anchor_label(span) -> str:
    return f"{span.anchor_id} | {source_reference(span)}"


def same_anchor(span, anchor_id: str) -> bool:
    return bool(span and span.anchor_id == anchor_id)


def truncate_text(text: str, limit: int) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


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


def issue_review_label(status: str) -> str:
    labels = {
        "unreviewed": "Unreviewed",
        "confirmed": "Confirmed",
        "false-positive": "False Positive",
        "needs-repair": "Needs Repair",
        "resolved": "Resolved",
    }
    return labels.get(status, status.replace("-", " ").title())


def repair_progress_summary(counts: dict[str, int]) -> str:
    if not counts:
        return "No saved repair progress"
    fixed = counts.get("fixed", 0)
    in_progress = counts.get("in-progress", 0)
    todo = counts.get("todo", 0)
    false_positive = counts.get("false-positive", 0)
    wont_fix = counts.get("wont-fix", 0)
    return f"{fixed} fixed, {in_progress} in progress, {todo} to do, {false_positive} false positive, {wont_fix} won't fix"


def issue_review_summary(counts: dict[str, int]) -> str:
    if not counts:
        return "No issue reviews"
    confirmed = counts.get("confirmed", 0)
    false_positive = counts.get("false-positive", 0)
    needs_repair = counts.get("needs-repair", 0)
    resolved = counts.get("resolved", 0)
    return f"{confirmed} confirmed, {needs_repair} needs repair, {resolved} resolved, {false_positive} false positive"


def revision_recheck_summary(counts: dict[str, int]) -> str:
    if not counts:
        return "No revision tests"
    improved = counts.get("improved", 0)
    still_weak = counts.get("still-weak", 0)
    new_issue = counts.get("introduces-new-issue", 0)
    return f"{improved} improved, {still_weak} still weak, {new_issue} new issue"


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
