"""Public API for the non-AI Gauntlet analyzer."""

from .analysis import analyze_loaded_document, analyze_paper_text
from .benchmarks import BenchmarkComparison, BenchmarkSample, list_benchmark_samples, run_benchmark_sample
from .document_loader import LoadedDocument, load_document_from_bytes, load_document_from_path
from .models import AnalysisReport, SourceSpan
from .refinement import ProviderSelection, RefinementReport, run_provider_refinement, run_refinement

__all__ = [
    "AnalysisReport",
    "BenchmarkComparison",
    "BenchmarkSample",
    "LoadedDocument",
    "ProviderSelection",
    "RefinementReport",
    "SourceSpan",
    "analyze_loaded_document",
    "analyze_paper_text",
    "list_benchmark_samples",
    "load_document_from_bytes",
    "load_document_from_path",
    "run_benchmark_sample",
    "run_provider_refinement",
    "run_refinement",
]
