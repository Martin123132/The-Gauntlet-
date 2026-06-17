from __future__ import annotations

import re

from .models import DocumentQualityIssue, DocumentQualityReport, SourceSpan


def assess_document_quality(
    text: str,
    source_spans: list[SourceSpan] | None = None,
    source_name: str = "uploaded document",
    file_size_bytes: int | None = None,
) -> DocumentQualityReport:
    source_spans = source_spans or []
    words = re.findall(r"\b[\w'-]+\b", text)
    sentences = [span for span in source_spans if span.text.strip()]
    character_count = len(text)
    word_count = len(words)
    sentence_count = len(sentences)
    issues: list[DocumentQualityIssue] = []
    lower_name = source_name.lower()

    if not text.strip():
        issues.append(
            DocumentQualityIssue(
                type="No readable text",
                severity="high",
                message="The document loader did not extract readable text.",
                recovery="If this is a PDF, it may be scanned images. Run OCR or export a text-based PDF before analyzing.",
            )
        )
    elif word_count < 80:
        issues.append(
            DocumentQualityIssue(
                type="Very short extraction",
                severity="high" if lower_name.endswith(".pdf") else "medium",
                message=f"Only {word_count} words were extracted, which may be too little for a fair paper verdict.",
                recovery="Check that the upload is the full paper and not a scanned/preview page. Try TXT/DOCX export if available.",
            )
        )

    if lower_name.endswith(".pdf") and word_count < 50:
        issues.append(
            DocumentQualityIssue(
                type="Scanned PDF suspected",
                severity="high",
                message="A PDF with very little extracted text often means the pages are images rather than selectable text.",
                recovery="Run OCR first, then upload the OCR/text version.",
            )
        )

    if text.strip() and not source_spans:
        issues.append(
            DocumentQualityIssue(
                type="Missing source anchors",
                severity="medium",
                message="Text was extracted, but no sentence-level source anchors were created.",
                recovery="Try a cleaner PDF/DOCX export so claims and findings can point back to exact source snippets.",
            )
        )

    if word_count >= 80:
        symbol_ratio = count_symbol_characters(text) / max(1, character_count)
        if symbol_ratio > 0.28:
            issues.append(
                DocumentQualityIssue(
                    type="Symbol-heavy extraction",
                    severity="medium",
                    message=f"About {symbol_ratio:.0%} of extracted characters are symbols, which can happen with equation dumps or broken PDF extraction.",
                    recovery="Inspect the Source Reader. If sentences look fragmented, try exporting the paper as TXT/DOCX.",
                )
            )

        short_word_ratio = sum(1 for word in words if len(word) == 1) / max(1, word_count)
        if short_word_ratio > 0.26:
            issues.append(
                DocumentQualityIssue(
                    type="Fragmented text",
                    severity="medium",
                    message=f"About {short_word_ratio:.0%} of extracted tokens are single-character fragments.",
                    recovery="This often means columns, ligatures, or OCR spacing broke during extraction. Try another export format.",
                )
            )

        reference_score = reference_density(text, word_count)
        if reference_score > 0.18:
            issues.append(
                DocumentQualityIssue(
                    type="Reference-heavy extraction",
                    severity="low",
                    message="The extracted text appears to contain a high share of references or citation-like material.",
                    recovery="Check whether the upload is mostly bibliography, supplementary references, or an extraction that overemphasized the reference section.",
                )
            )

    score = quality_score(issues)
    status = "fail" if any(issue.severity == "high" for issue in issues) else "warn" if issues else "ok"
    return DocumentQualityReport(
        status=status,
        score=score,
        word_count=word_count,
        sentence_count=sentence_count,
        character_count=character_count,
        source_span_count=len(source_spans),
        file_size_bytes=file_size_bytes,
        issues=issues,
    )


def count_symbol_characters(text: str) -> int:
    allowed_punctuation = set(".,;:!?()[]{}'\"/-")
    return sum(
        1
        for character in text
        if not character.isalnum() and not character.isspace() and character not in allowed_punctuation
    )


def reference_density(text: str, word_count: int) -> float:
    citation_like = len(re.findall(r"\b(?:18|19|20)\d{2}\b|doi:|et al\.|references|bibliography", text, re.I))
    return citation_like / max(1, word_count)


def quality_score(issues: list[DocumentQualityIssue]) -> float:
    score = 1.0
    for issue in issues:
        if issue.severity == "high":
            score -= 0.42
        elif issue.severity == "medium":
            score -= 0.18
        else:
            score -= 0.08
    return round(max(0.0, min(1.0, score)), 3)
