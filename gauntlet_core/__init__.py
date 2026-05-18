"""Public API for the non-AI Gauntlet analyzer."""

from .analysis import analyze_loaded_document, analyze_paper_text
from .batch import BatchScanItem, batch_items_to_csv, batch_items_to_json, build_batch_report_bundle
from .benchmarks import BenchmarkComparison, BenchmarkSample, list_benchmark_samples, run_benchmark_sample
from .document_loader import LoadedDocument, load_document_from_bytes, load_document_from_path
from .models import AnalysisReport, SourceSpan
from .report_bundle import build_report_bundle
from .refinement import ProviderSelection, RefinementReport, run_provider_refinement, run_refinement
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
    "LoadedDocument",
    "ProviderSelection",
    "RefinementReport",
    "SavedRun",
    "SavedRunSummary",
    "SourceSpan",
    "analyze_loaded_document",
    "analyze_paper_text",
    "batch_items_to_csv",
    "batch_items_to_json",
    "build_batch_report_bundle",
    "build_report_bundle",
    "delete_saved_run",
    "list_benchmark_samples",
    "list_saved_runs",
    "load_document_from_bytes",
    "load_document_from_path",
    "load_saved_run",
    "run_benchmark_sample",
    "run_provider_refinement",
    "run_refinement",
    "save_analysis_run",
    "update_saved_run_notes",
]
