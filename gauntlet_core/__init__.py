"""Public API for the non-AI Gauntlet analyzer."""

from .analysis import analyze_loaded_document, analyze_paper_text
from .action_plan import ReviewerAction, action_plan_to_markdown, build_reviewer_action_plan
from .batch import (
    BatchScanItem,
    batch_items_to_csv,
    batch_items_to_html,
    batch_items_to_json,
    build_demo_batch_items,
    build_batch_report_bundle,
    filter_batch_items,
    sort_batch_items,
)
from .benchmarks import BenchmarkComparison, BenchmarkSample, list_benchmark_samples, run_benchmark_sample
from .document_loader import LoadedDocument, load_document_from_bytes, load_document_from_path
from .models import AnalysisReport, SourceSpan
from .report_bundle import build_report_bundle
from .refinement import ProviderSelection, RefinementReport, run_provider_refinement, run_refinement
from .share import (
    DemoShareSummary,
    build_demo_share_pack,
    build_demo_share_summary,
    build_share_card_html,
    build_share_card_svg,
    build_x_post,
)
from .workspace import (
    SavedRun,
    SavedRunSummary,
    delete_saved_run,
    list_saved_runs,
    load_saved_run,
    save_analysis_run,
    update_saved_run_notes,
)

__all__ = [
    "AnalysisReport",
    "BatchScanItem",
    "BenchmarkComparison",
    "BenchmarkSample",
    "DemoShareSummary",
    "LoadedDocument",
    "ProviderSelection",
    "RefinementReport",
    "ReviewerAction",
    "SavedRun",
    "SavedRunSummary",
    "SourceSpan",
    "analyze_loaded_document",
    "analyze_paper_text",
    "action_plan_to_markdown",
    "batch_items_to_csv",
    "batch_items_to_html",
    "batch_items_to_json",
    "build_demo_batch_items",
    "build_reviewer_action_plan",
    "build_batch_report_bundle",
    "build_report_bundle",
    "build_demo_share_pack",
    "build_demo_share_summary",
    "build_share_card_html",
    "build_share_card_svg",
    "build_x_post",
    "delete_saved_run",
    "filter_batch_items",
    "list_benchmark_samples",
    "list_saved_runs",
    "load_document_from_bytes",
    "load_document_from_path",
    "load_saved_run",
    "run_benchmark_sample",
    "run_provider_refinement",
    "run_refinement",
    "save_analysis_run",
    "sort_batch_items",
    "update_saved_run_notes",
]
