from __future__ import annotations

from gauntlet_core.extraction_preview import preview_document_extraction, preview_pasted_text


def test_preview_document_extraction_reports_usable_text():
    preview = preview_document_extraction(
        "paper.txt",
        b"The framework resolves the anomaly because the mechanism uses 12 measured observations.",
    )

    assert preview.can_analyze
    assert preview.status in {"ok", "warn", "fail"}
    assert preview.quality.word_count > 0
    assert preview.quality.source_span_count >= 1
    assert "framework resolves" in preview.text_preview


def test_preview_document_extraction_returns_rescue_for_unsupported_file():
    preview = preview_document_extraction("paper.csv", b"title,body\nx,y")

    assert not preview.can_analyze
    assert preview.status == "fail"
    assert "Unsupported file type" in preview.error
    assert any("PDF, DOCX, TXT, or MD" in suggestion for suggestion in preview.suggestions)


def test_preview_pasted_text_gives_paste_source_and_rescue_guidance():
    preview = preview_pasted_text("copied-paper.txt", "This is copied text from a paper.")

    assert preview.source_name == "copied-paper.txt"
    assert preview.document is not None
    assert preview.document.text.startswith("This is copied")
    assert any("Paste Text Instead" in suggestion or "Extraction looks usable" in suggestion for suggestion in preview.suggestions)
