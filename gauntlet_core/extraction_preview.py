from __future__ import annotations

from dataclasses import dataclass, field

from .document_loader import LoadedDocument, build_source_spans, load_document_from_bytes
from .document_quality import assess_document_quality
from .models import DocumentQualityReport
from .ocr import OcrReadinessReport


@dataclass(frozen=True)
class ExtractionPreview:
    source_name: str
    status: str
    quality: DocumentQualityReport
    text_preview: str = ""
    page_count: int = 0
    error: str = ""
    suggestions: tuple[str, ...] = field(default_factory=tuple)
    document: LoadedDocument | None = field(default=None, repr=False, compare=False)

    @property
    def can_analyze(self) -> bool:
        return self.status in {"ok", "warn"} and bool(self.document and self.document.text.strip())


def preview_document_extraction(
    filename: str,
    data: bytes,
    ocr_readiness: OcrReadinessReport | None = None,
) -> ExtractionPreview:
    try:
        document = load_document_from_bytes(filename, data)
    except Exception as exc:
        quality = assess_document_quality("", source_name=filename, file_size_bytes=len(data))
        return ExtractionPreview(
            source_name=filename,
            status="fail",
            quality=quality,
            error=str(exc),
            suggestions=extraction_rescue_suggestions(quality, str(exc), ocr_readiness),
        )

    quality = assess_document_quality(
        document.text,
        source_spans=document.source_spans,
        source_name=document.filename,
        file_size_bytes=document.file_size_bytes,
    )
    page_numbers = {span.page_number for span in document.source_spans if span.page_number is not None}
    return ExtractionPreview(
        source_name=document.filename,
        status=quality.status,
        quality=quality,
        text_preview=compact_preview(document.text),
        page_count=len(page_numbers),
        suggestions=extraction_rescue_suggestions(quality, ocr_readiness=ocr_readiness),
        document=document,
    )


def preview_pasted_text(
    source_name: str,
    text: str,
    ocr_readiness: OcrReadinessReport | None = None,
) -> ExtractionPreview:
    filename = source_name.strip() or "pasted-paper.txt"
    source_spans = build_source_spans(text)
    document = LoadedDocument(
        filename=filename,
        text=text,
        source_spans=source_spans,
        file_size_bytes=len(text.encode("utf-8")),
        extension=".txt",
    )
    quality = assess_document_quality(
        text,
        source_spans=source_spans,
        source_name=filename,
        file_size_bytes=document.file_size_bytes,
    )
    return ExtractionPreview(
        source_name=filename,
        status=quality.status,
        quality=quality,
        text_preview=compact_preview(text),
        suggestions=extraction_rescue_suggestions(quality, ocr_readiness=ocr_readiness),
        document=document,
    )


def extraction_rescue_suggestions(
    quality: DocumentQualityReport,
    error: str = "",
    ocr_readiness: OcrReadinessReport | None = None,
) -> tuple[str, ...]:
    suggestions: list[str] = []
    for issue in quality.issues:
        if issue.recovery and issue.recovery not in suggestions:
            suggestions.append(issue.recovery)
    if error and "unsupported file type" in error.lower():
        suggestions.append("Upload a PDF, DOCX, TXT, or MD file.")
    if quality.status in {"warn", "fail"}:
        if ocr_readiness:
            suggestions.append(ocr_status_suggestion(ocr_readiness))
        suggestions.extend(
            [
                "If the paper is a scanned PDF, use OCR first or upload a selectable-text version.",
                "Try exporting the paper as TXT, DOCX, or Markdown and run the same checker again.",
                "Use Paste Text Instead if you can copy the paper text from a browser, PDF viewer, or repository page.",
            ]
        )
    if not suggestions:
        suggestions.append("Extraction looks usable. Continue to analysis, then inspect Source Reader for exact snippets.")
    return tuple(dict.fromkeys(suggestions))


def ocr_status_suggestion(readiness: OcrReadinessReport) -> str:
    if readiness.status == "available":
        return "OCR appears available locally. For scanned PDFs, run OCR outside The Gauntlet or wait for optional OCR processing in a future release."
    if readiness.status == "partial":
        return "OCR is partially installed locally. Finish installing Tesseract and Python OCR packages before relying on scanned-PDF recovery."
    return "OCR is not installed locally. Install Tesseract only if you need scanned-PDF recovery; selectable-text PDFs, DOCX, TXT, and pasted text still work."


def compact_preview(text: str, limit: int = 900) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return f"{clean[:limit].rstrip()}..."
