"""Public API for the non-AI Gauntlet analyzer."""

from .analysis import analyze_paper_text
from .models import AnalysisReport

__all__ = ["AnalysisReport", "analyze_paper_text"]
