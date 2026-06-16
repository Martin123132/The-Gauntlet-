import json

from gauntlet_core import analyze_paper_text
from gauntlet_core.document_quality import assess_document_quality
from gauntlet_core.models import AnalysisReport, SourceSpan, analysis_report_from_dict


def test_document_quality_passes_clean_extraction():
    text = " ".join(
        [
            "The framework resolves the anomaly through a measured mechanism with 12 observations.",
            "The method compares three datasets and reports a stable prediction with RMSE = 0.03.",
            "The discussion limits the claim to the calibrated sample and names the boundary condition.",
        ]
        * 12
    )
    spans = [SourceSpan("S1", "Document", 1, None, 0, 90, text[:90])]

    quality = assess_document_quality(text, source_spans=spans, source_name="paper.txt")

    assert quality.status == "ok"
    assert quality.score == 1.0
    assert not quality.issues


def test_document_quality_flags_scanned_pdf_like_extraction():
    quality = assess_document_quality("", source_spans=[], source_name="paper.pdf", file_size_bytes=250_000)

    assert quality.status == "fail"
    assert any(issue.type == "No readable text" for issue in quality.issues)
    assert any(issue.type == "Scanned PDF suspected" for issue in quality.issues)
    assert quality.score < 0.5


def test_document_quality_flags_fragmented_symbol_heavy_text():
    text = " ".join(["x = y + z * @@@ ### *** === +++ !!! ??? %%% ^^^ a b c d e f g h i j k"] * 20)

    quality = assess_document_quality(text, source_spans=[], source_name="broken.pdf")

    issue_types = {issue.type for issue in quality.issues}
    assert quality.status in {"warn", "fail"}
    assert "Missing source anchors" in issue_types
    assert "Fragmented text" in issue_types
    assert "Symbol-heavy extraction" in issue_types


def test_analysis_report_includes_document_quality_json_markdown_and_restore():
    report = analyze_paper_text(
        "The paper resolves the paradox because the mechanism is measured by 12 tests.",
        source_name="paper.txt",
    )
    data = json.loads(report.to_json())
    restored = analysis_report_from_dict(data)

    assert data["document_quality"]["status"] in {"ok", "warn", "fail"}
    assert "Document Extraction Quality" in report.to_markdown()
    assert restored.document_quality.status == report.document_quality.status


def test_old_report_json_restores_with_unknown_document_quality():
    report = analyze_paper_text(
        "The paper resolves the paradox because the mechanism is measured by 12 tests.",
        source_name="paper.txt",
    )
    data = report.to_dict()
    data.pop("document_quality")

    restored = AnalysisReport.from_dict(data)

    assert restored.document_quality.status == "unknown"
