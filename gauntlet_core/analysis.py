from __future__ import annotations

from dataclasses import dataclass
import math
import re

from .contradiction import ClaimPair, ContradictionEngine, content_words, has_negation
from .models import (
    AnalysisReport,
    AuditEvent,
    ClaimResult,
    EvidenceLink,
    EvidenceProfile,
    Finding,
    RubricScore,
    SourceSpan,
    Verdict,
    utc_now_iso,
)


@dataclass(frozen=True)
class DocumentSection:
    title: str
    text: str


@dataclass(frozen=True)
class DocumentSentence:
    text: str
    section: str
    index: int
    source_span: SourceSpan | None = None


@dataclass(frozen=True)
class ClaimCandidate:
    sentence: DocumentSentence
    trigger_terms: list[str]


CLAIM_INDICATORS = {
    "resolves",
    "solve",
    "solves",
    "explains",
    "accounts for",
    "demonstrates",
    "shows",
    "proves",
    "establishes",
    "validates",
    "supports",
    "indicates",
    "suggests",
    "implies",
    "reveals",
    "addresses",
    "eliminates",
    "reconciles",
    "unifies",
    "therefore",
    "thus",
    "consequently",
    "because",
    "due to",
    "predicts",
}

RESOLUTION_INDICATORS = {
    "resolves",
    "solve",
    "solves",
    "eliminates",
    "reconciles",
    "unifies",
    "addresses",
    "accounts for",
    "explains",
    "fixes",
    "removes",
}

PROBLEM_INDICATORS = {
    "paradox",
    "contradiction",
    "problem",
    "issue",
    "conflict",
    "inconsistency",
    "discrepancy",
    "anomaly",
    "violation",
    "failure",
    "breakdown",
    "crisis",
    "tension",
    "puzzle",
}

MECHANISM_INDICATORS = {
    "because",
    "through",
    "by",
    "via",
    "using",
    "mechanism",
    "method",
    "process",
    "principle",
    "framework",
    "model",
    "equation",
    "formula",
    "calculation",
    "proof",
    "derivation",
    "causal",
}

DETAIL_INDICATORS = {
    "specifically",
    "precisely",
    "for example",
    "such as",
    "including",
    "namely",
    "i.e.",
    "for instance",
}

EVIDENCE_TERMS = {
    "data",
    "observation",
    "measurement",
    "experiment",
    "test",
    "evidence",
    "result",
    "finding",
    "detection",
    "analysis",
    "correlation",
    "fit",
    "accuracy",
    "precision",
    "dataset",
    "sample",
}

METHODOLOGY_TERMS = {
    "sample",
    "method",
    "methodology",
    "control",
    "baseline",
    "trial",
    "replication",
    "prediction",
    "statistical",
    "confidence interval",
    "p-value",
    "rmse",
    "r2",
}

COMPARISON_MARKERS = {
    "classical",
    "traditional",
    "standard",
    "conventional",
    "versus",
    "vs",
    "compared to",
    "unlike",
    "instead of",
    "rather than",
}

BACKGROUND_MARKERS = {
    "prior work",
    "previous work",
    "previous theory",
    "earlier model",
    "existing literature",
    "literature",
    "historically",
    "reference",
    "references",
    "cited",
    "reported by",
}

TENTATIVE_MARKERS = {
    "may",
    "might",
    "could",
    "hypothesis",
    "hypothesize",
    "tentative",
    "possible",
    "possibly",
    "preliminary",
    "suggest",
    "suggests",
    "proposal",
    "propose",
    "proposes",
}

LIMITATION_MARKERS = {
    "limited to",
    "only under",
    "only within",
    "within the",
    "outside that scope",
    "outside this scope",
    "outside the scope",
    "not apply",
    "does not apply",
    "not tested",
    "boundary condition",
    "scope is",
    "scoped to",
    "calibrated sample",
}

SECTION_HEADINGS = {
    "abstract",
    "summary",
    "introduction",
    "background",
    "theory",
    "framework",
    "method",
    "methods",
    "methodology",
    "evidence",
    "results",
    "analysis",
    "discussion",
    "limitations",
    "conclusion",
    "references",
}

THEORY_AS_FACT_PATTERNS = (
    r"\b(theory|model|framework)\s+(proves|shows|says|dictates)\s+that\b",
    r"\b(impossible|certain|absolute|undeniable)\s+because\s+(theory|model|framework)\b",
    r"\b(current|standard)\s+(theory|model)\s+(therefore\s+)?(proves|forbids|requires)\b",
)


def analyze_paper_text(
    text: str,
    source_name: str = "uploaded document",
    source_spans: list[SourceSpan] | None = None,
) -> AnalysisReport:
    sections = parse_document_sections(text)
    sentences = split_section_sentences(sections)
    cleaned_text = normalize_document_text(" ".join(section.text for section in sections))
    aligned_spans = align_source_spans(sentences, source_spans, cleaned_text)
    sentences = attach_source_spans(sentences, aligned_spans)
    evidence_links = extract_evidence_links(sentences)
    evidence = assess_evidence(cleaned_text, evidence_links)
    claim_candidates = extract_claim_candidates(sentences)
    claims = analyze_claims(claim_candidates, evidence_links)
    findings = find_internal_contradictions(sentences)
    findings.extend(find_barrier_findings(claims, sentences))
    findings = assign_finding_ids(dedupe_findings(findings)[:18])
    verdict_rubric = build_verdict_rubric(claims, findings, evidence)
    verdict = determine_verdict(claims, findings, evidence)
    confidence = calculate_confidence(claims, findings, evidence, verdict)
    summary = build_summary(verdict, claims, findings, evidence)
    audit_events = build_report_audit_events(sections, sentences, claims, findings, evidence, verdict)
    issue_brief = build_issue_brief(claims, findings, evidence, verdict)
    return AnalysisReport(
        source_name=source_name,
        verdict=verdict,
        confidence=confidence,
        created_at=utc_now_iso(),
        word_count=len(re.findall(r"\b\w+\b", cleaned_text)),
        sentence_count=len(sentences),
        claims=claims,
        findings=findings,
        evidence=evidence,
        summary=summary,
        sections=[section.title for section in sections],
        audit_events=audit_events,
        verdict_rubric=verdict_rubric,
        issue_brief=issue_brief,
        source_spans=aligned_spans,
    )


def analyze_loaded_document(document) -> AnalysisReport:
    return analyze_paper_text(
        document.text,
        source_name=getattr(document, "filename", "uploaded document"),
        source_spans=getattr(document, "source_spans", None),
    )


def parse_document_sections(text: str) -> list[DocumentSection]:
    text = text.replace("\x00", " ")
    text = re.sub(r"-\s*\n\s*", "", text)
    lines = [line.strip() for line in text.splitlines()]
    sections: list[DocumentSection] = []
    current_title = "Document"
    current_lines: list[str] = []

    for line in lines:
        if not line:
            continue
        heading = detect_heading(line)
        if heading:
            if current_lines:
                sections.append(DocumentSection(current_title, normalize_document_text(" ".join(current_lines))))
                current_lines = []
            current_title = heading
            continue
        current_lines.append(line)

    if current_lines:
        sections.append(DocumentSection(current_title, normalize_document_text(" ".join(current_lines))))

    return [section for section in sections if section.text] or [DocumentSection("Document", normalize_document_text(text))]


def detect_heading(line: str) -> str | None:
    stripped = re.sub(r"^#+\s*", "", line).strip().strip(":")
    lowered = stripped.lower()
    if lowered in SECTION_HEADINGS:
        return stripped.title()
    numbered = re.sub(r"^\d+(?:\.\d+)*\s+", "", lowered).strip()
    if numbered in SECTION_HEADINGS:
        return numbered.title()
    if len(stripped.split()) <= 4 and not re.search(r"[.!?]$", stripped) and numbered in SECTION_HEADINGS:
        return stripped.title()
    return None


def normalize_document_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_section_sentences(sections: list[DocumentSection]) -> list[DocumentSentence]:
    sentences: list[DocumentSentence] = []
    for section in sections:
        parts = re.split(r"(?<=[.!?])\s+", section.text)
        for part in parts:
            cleaned = part.strip()
            if len(cleaned) >= 20:
                sentences.append(DocumentSentence(cleaned, section.title, len(sentences) + 1))
    return sentences


def split_sentences(text: str) -> list[str]:
    return [sentence.text for sentence in split_section_sentences([DocumentSection("Document", normalize_document_text(text))])]


def align_source_spans(
    sentences: list[DocumentSentence],
    provided_spans: list[SourceSpan] | None,
    cleaned_text: str,
) -> list[SourceSpan]:
    provided_spans = provided_spans or []
    used_span_ids: set[str] = set()
    aligned: list[SourceSpan] = []
    search_from = 0
    for sentence in sentences:
        matched = find_matching_source_span(sentence.text, provided_spans, used_span_ids)
        if matched:
            used_span_ids.add(matched.anchor_id)
            char_start = matched.char_start
            char_end = matched.char_end
            page_number = matched.page_number
        else:
            char_start = cleaned_text.find(sentence.text, search_from)
            if char_start < 0:
                char_start = cleaned_text.find(sentence.text)
            if char_start < 0:
                char_start = -1
                char_end = -1
            else:
                char_end = char_start + len(sentence.text)
                search_from = char_end
            page_number = None
        aligned.append(
            SourceSpan(
                anchor_id=f"S{sentence.index}",
                section=sentence.section,
                sentence_index=sentence.index,
                page_number=page_number,
                char_start=char_start,
                char_end=char_end,
                text=sentence.text,
            )
        )
    return aligned


def find_matching_source_span(
    sentence_text: str,
    source_spans: list[SourceSpan],
    used_span_ids: set[str],
) -> SourceSpan | None:
    target = source_key(sentence_text)
    if not target:
        return None
    best: tuple[float, SourceSpan] | None = None
    for span in source_spans:
        if span.anchor_id in used_span_ids:
            continue
        candidate = source_key(span.text)
        if not candidate:
            continue
        if candidate == target:
            return span
        overlap = jaccard(set(target.split()), set(candidate.split()))
        contains_bonus = 0.15 if target in candidate or candidate in target else 0.0
        score = overlap + contains_bonus
        if score >= 0.72 and (best is None or score > best[0]):
            best = (score, span)
    return best[1] if best else None


def attach_source_spans(sentences: list[DocumentSentence], source_spans: list[SourceSpan]) -> list[DocumentSentence]:
    spans_by_index = {span.sentence_index: span for span in source_spans}
    return [
        DocumentSentence(sentence.text, sentence.section, sentence.index, spans_by_index.get(sentence.index))
        for sentence in sentences
    ]


def source_key(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def extract_claim_candidates(sentences: list[DocumentSentence], limit: int = 28) -> list[ClaimCandidate]:
    candidates: list[ClaimCandidate] = []
    for sentence in sentences:
        lower = sentence.text.lower()
        if is_reference_like_sentence(sentence.text):
            continue
        triggers = sorted(indicator for indicator in CLAIM_INDICATORS if indicator in lower)
        problem_reference = any(problem in lower for problem in PROBLEM_INDICATORS)
        theory_reference = any(word in lower for word in ["model", "framework", "theory", "paper", "approach", "method"])
        modal_resolution = bool(re.search(r"\b(can|will|must|should|would|may|might|could)\b.*\b(resolve|solve|explain|reconcile|predict)\b", lower))
        background_only = is_background_context(lower) and not any(indicator in lower for indicator in RESOLUTION_INDICATORS)
        if triggers or (problem_reference and theory_reference) or modal_resolution:
            if background_only:
                continue
            candidates.append(ClaimCandidate(sentence, triggers or ["problem reference"]))
    return dedupe_claim_candidates(candidates)[:limit]


def extract_claims(sentences: list[str], limit: int = 24) -> list[str]:
    wrapped = [DocumentSentence(sentence, "Document", index + 1) for index, sentence in enumerate(sentences)]
    return [candidate.sentence.text for candidate in extract_claim_candidates(wrapped, limit)]


def analyze_claims(candidates: list[ClaimCandidate], evidence_links: list[EvidenceLink] | None = None) -> list[ClaimResult]:
    evidence_links = evidence_links or []
    results: list[ClaimResult] = []
    for index, candidate in enumerate(candidates, start=1):
        claim = candidate.sentence.text
        lower = claim.lower()
        linked_evidence = link_evidence_to_claim(candidate.sentence, evidence_links)
        strong_linked_evidence = [link for link in linked_evidence if link.confidence >= 0.42]
        tentative_claim = is_tentative_language(lower)
        has_mechanism = any(indicator in lower for indicator in MECHANISM_INDICATORS)
        has_detail = any(indicator in lower for indicator in DETAIL_INDICATORS)
        evidence_hits = count_terms(lower, EVIDENCE_TERMS)
        methodology_hits = count_terms(lower, METHODOLOGY_TERMS)
        number_hits = len(re.findall(r"\d+(?:\.\d+)?%?", claim))
        citation_hits = count_citations(claim)
        equation_hits = count_math_content(claim)
        linked_strength = sum(link.confidence for link in linked_evidence[:4]) / max(1, min(4, len(linked_evidence)))

        mechanism_score = 0.28 if has_mechanism else 0.0
        detail_score = 0.12 if has_detail else 0.0
        local_evidence_score = min(
            0.26,
            (evidence_hits + methodology_hits) * 0.045 + number_hits * 0.04 + citation_hits * 0.07,
        )
        linked_evidence_score = min(0.22, linked_strength * 0.26)
        math_score = min(0.12, equation_hits * 0.055)
        quality = clamp(0.10 + mechanism_score + detail_score + local_evidence_score + linked_evidence_score + math_score, 0.05, 0.98)
        if tentative_claim:
            quality = clamp(quality - 0.16, 0.05, 0.82)

        gaps: list[str] = []
        if not has_mechanism:
            gaps.append("mechanism missing")
        if not strong_linked_evidence and evidence_hits + methodology_hits + number_hits + citation_hits == 0:
            gaps.append("evidence not linked")
        if not has_detail:
            gaps.append("details not specific")
        if any(indicator in lower for indicator in RESOLUTION_INDICATORS) and not any(problem in lower for problem in PROBLEM_INDICATORS):
            gaps.append("problem scope unclear")

        if quality >= 0.72 and has_mechanism and strong_linked_evidence and not tentative_claim and "evidence not linked" not in gaps:
            status = "resolved"
        elif quality >= 0.40 or has_mechanism or linked_evidence:
            status = "partial"
        else:
            status = "failed"

        rubric_scores = [
            RubricScore("Mechanism", round(mechanism_score / 0.28 if mechanism_score else 0.0, 3), 0.28, "Mechanism language found" if has_mechanism else "No explicit mechanism language"),
            RubricScore("Specificity", 1.0 if has_detail else 0.0, 0.12, "Specific detail marker found" if has_detail else "No concrete detail marker"),
            RubricScore("Local evidence", round(min(1.0, local_evidence_score / 0.26), 3), 0.26, "Evidence markers in the claim sentence"),
            RubricScore("Linked evidence", round(min(1.0, linked_evidence_score / 0.22), 3), 0.22, "Nearby or overlapping evidence snippets"),
            RubricScore("Math/proof", round(min(1.0, math_score / 0.12), 3), 0.12, "Math or proof markers"),
        ]
        audit_events = [
            AuditEvent("claim extraction", "matched", f"Triggered by: {', '.join(candidate.trigger_terms)}"),
            AuditEvent("mechanism check", "pass" if has_mechanism else "fail", "Mechanism language present" if has_mechanism else "Needs a named process, equation, proof, or causal bridge", mechanism_score),
            AuditEvent("evidence link", "pass" if linked_evidence else "warn", f"{len(linked_evidence)} evidence snippets linked", linked_evidence_score),
            AuditEvent("guardrail scan", "warn" if tentative_claim else "pass", "Tentative or hypothesis language kept below RESOLVES" if tentative_claim else "No tentative-resolution guardrail triggered"),
            AuditEvent("claim verdict", status, f"Quality score {quality:.2f}", quality),
        ]
        results.append(
            ClaimResult(
                claim=claim,
                status=status,
                quality=round(quality, 3),
                mechanism="provided" if has_mechanism else "missing",
                evidence_strength=round(clamp(local_evidence_score + linked_evidence_score + math_score + citation_hits * 0.04, 0.0, 0.95), 3),
                gaps=gaps,
                id=f"C{index}",
                section=candidate.sentence.section,
                sentence_index=candidate.sentence.index,
                evidence_links=linked_evidence,
                rubric_scores=rubric_scores,
                audit_events=audit_events,
                repair_suggestion=repair_suggestion_for_gaps(gaps),
                trigger_terms=candidate.trigger_terms,
                source_span=candidate.sentence.source_span,
            )
        )
    return results


def extract_evidence_links(sentences: list[DocumentSentence]) -> list[EvidenceLink]:
    links: list[EvidenceLink] = []
    for sentence in sentences:
        lower = sentence.text.lower()
        evidence_count = count_terms(lower, EVIDENCE_TERMS)
        methodology_count = count_terms(lower, METHODOLOGY_TERMS)
        numbers = len(re.findall(r"\b\d+(?:\.\d+)?%?\b|r\^?2\s*=|rmse\s*=|p\s*[<=>]", lower))
        citations = count_citations(sentence.text)
        math_content = count_math_content(sentence.text)
        if evidence_count + methodology_count + numbers + citations + math_content == 0:
            continue
        evidence_type = "mixed"
        if citations:
            evidence_type = "citation"
        elif numbers:
            evidence_type = "quantitative"
        elif math_content:
            evidence_type = "math"
        elif methodology_count:
            evidence_type = "method"
        confidence = clamp(0.24 + citations * 0.16 + numbers * 0.07 + math_content * 0.07 + evidence_count * 0.04 + methodology_count * 0.04, 0.2, 0.95)
        if is_reference_like_sentence(sentence.text):
            confidence = min(confidence, 0.35)
        links.append(
            EvidenceLink(
                id=f"E{len(links) + 1}",
                type=evidence_type,
                snippet=trim_sentence(sentence.text, 220),
                section=sentence.section,
                sentence_index=sentence.index,
                confidence=round(confidence, 3),
                source_span=sentence.source_span,
            )
        )
    return links


def link_evidence_to_claim(claim: DocumentSentence, evidence_links: list[EvidenceLink]) -> list[EvidenceLink]:
    claim_words = content_words(claim.text)
    scored: list[tuple[float, EvidenceLink]] = []
    for link in evidence_links:
        evidence_words = content_words(link.snippet)
        overlap = jaccard(claim_words, evidence_words)
        if is_reference_like_sentence(link.snippet) and overlap < 0.18:
            continue
        proximity = max(0.0, 1.0 - abs(claim.index - link.sentence_index) / 8)
        same_section = 0.22 if claim.section == link.section else 0.0
        score = overlap * 0.55 + proximity * 0.30 + same_section
        if score >= 0.20:
            scored.append((score, link))
    return [link for _, link in sorted(scored, key=lambda item: item[0], reverse=True)[:4]]


def assess_evidence(text: str, evidence_links: list[EvidenceLink] | None = None) -> EvidenceProfile:
    evidence_links = evidence_links or []
    lower = text.lower()
    quantitative = len(re.findall(r"\b\d+(?:\.\d+)?%?\b|r\^?2\s*=|rmse\s*=|p\s*[<=>]", lower))
    math_content = count_math_content(text)
    citations = count_citations(text)
    methodology = count_terms(lower, METHODOLOGY_TERMS)
    evidence_terms = count_terms(lower, EVIDENCE_TERMS)
    section_counts: dict[str, int] = {}
    for link in evidence_links:
        section_counts[link.section] = section_counts.get(link.section, 0) + 1
    score = (
        0.14
        + 0.24 * min(1.0, quantitative / 8)
        + 0.20 * min(1.0, math_content / 6)
        + 0.20 * min(1.0, citations / 6)
        + 0.14 * min(1.0, methodology / 8)
        + 0.10 * min(1.0, evidence_terms / 10)
        + 0.12 * min(1.0, len(evidence_links) / 8)
    )
    return EvidenceProfile(
        score=round(clamp(score, 0.0, 0.98), 3),
        quantitative_evidence=quantitative,
        mathematical_content=math_content,
        citations=citations,
        methodology_terms=methodology,
        evidence_terms=evidence_terms,
        linked_evidence=len(evidence_links),
        section_counts=section_counts,
        evidence_links=evidence_links[:18],
    )


def find_internal_contradictions(sentences: list[DocumentSentence] | list[str]) -> list[Finding]:
    normalized_sentences = normalize_sentence_inputs(sentences)
    engine = ContradictionEngine()
    findings: list[Finding] = []
    max_pairs = 520
    checked = 0
    for i, first in enumerate(normalized_sentences):
        for j, second in enumerate(normalized_sentences[i + 1 :], i + 1):
            if checked >= max_pairs:
                break
            checked += 1
            if is_comparison_context(first.text, second.text) or is_scoped_exception_pair(first.text, second.text):
                continue
            first_words = content_words(first.text)
            second_words = content_words(second.text)
            overlap = jaccard(first_words, second_words)
            if overlap < 0.20:
                continue
            contradiction = engine.detect(ClaimPair(f"s{first.index}-s{second.index}", first.text, second.text))
            if contradiction:
                findings.append(
                    Finding(
                        type=contradiction.type.value.replace("_", " ").title(),
                        severity=severity_for_score(contradiction.score),
                        sentence=trim_sentence(second.text),
                        related_sentence=trim_sentence(first.text),
                        explanation=contradiction.note,
                        repair_suggestion=contradiction.repair_suggestion,
                        confidence=round(contradiction.score, 2),
                        section=second.section,
                        trigger=f"overlap {overlap:.2f}",
                        source_span=second.source_span,
                        related_source_span=first.source_span,
                    )
                )
            elif has_negation(first.text) != has_negation(second.text) and overlap >= 0.42:
                findings.append(
                    Finding(
                        type="Potential Direct Negation",
                        severity="medium",
                        sentence=trim_sentence(second.text),
                        related_sentence=trim_sentence(first.text),
                        explanation="Two similar sentences appear to differ mainly by negation.",
                        repair_suggestion="Clarify whether these sentences refer to different scopes, dates, or assumptions.",
                        confidence=round(overlap, 2),
                        section=second.section,
                        trigger=f"negation polarity with overlap {overlap:.2f}",
                        source_span=second.source_span,
                        related_source_span=first.source_span,
                    )
                )
        if checked >= max_pairs:
            break

    findings.extend(find_circular_reasoning(normalized_sentences))
    findings.extend(find_scope_conflicts(normalized_sentences))
    findings.extend(find_theory_as_fact_language(normalized_sentences))
    return findings


def normalize_sentence_inputs(sentences: list[DocumentSentence] | list[str]) -> list[DocumentSentence]:
    if not sentences:
        return []
    if isinstance(sentences[0], DocumentSentence):
        return sentences  # type: ignore[return-value]
    return [DocumentSentence(str(sentence), "Document", index + 1) for index, sentence in enumerate(sentences)]


def find_circular_reasoning(sentences: list[DocumentSentence]) -> list[Finding]:
    because_sentences = [sentence for sentence in sentences if "because" in sentence.text.lower()]
    therefore_sentences = [sentence for sentence in sentences if "therefore" in sentence.text.lower()]
    for first in because_sentences:
        first_words = content_words(first.text)
        for second in therefore_sentences:
            if first.index == second.index:
                continue
            overlap = jaccard(first_words, content_words(second.text))
            if overlap >= 0.30 or (len(because_sentences) >= 2 and len(therefore_sentences) >= 2):
                return [
                    Finding(
                        type="Potential Circular Reasoning",
                        severity="low",
                        sentence=trim_sentence(first.text),
                        related_sentence=trim_sentence(second.text),
                        explanation="Repeated because/therefore reasoning with overlapping terms may be using the conclusion as support.",
                        repair_suggestion="Make premises, evidence, and conclusions explicit so the conclusion is not used as its own support.",
                        confidence=round(max(0.45, overlap), 2),
                        section=first.section,
                        trigger="because/therefore support loop",
                        source_span=first.source_span,
                        related_source_span=second.source_span,
                    )
                ]
    return []


def find_scope_conflicts(sentences: list[DocumentSentence]) -> list[Finding]:
    findings: list[Finding] = []
    absolute = re.compile(r"\b(all|always|every|never|none|universal|in every case|without exception)\b", re.I)
    caveat = re.compile(r"\b(except|unless|only when|under|in some cases|limited to|scope|boundary|however)\b", re.I)
    for index, sentence in enumerate(sentences):
        if not absolute.search(sentence.text):
            continue
        if is_scoped_universal(sentence.text) or is_background_context(sentence.text):
            continue
        window = sentences[max(0, index - 2) : min(len(sentences), index + 3)]
        caveats = [
            candidate
            for candidate in window
            if candidate.index != sentence.index
            and caveat.search(candidate.text)
            and not is_scope_limitation_context(candidate.text)
        ]
        if caveats:
            findings.append(
                Finding(
                    type="Scope Conflict",
                    severity="medium",
                    sentence=trim_sentence(sentence.text),
                    related_sentence=trim_sentence(caveats[0].text),
                    explanation="A broad universal claim appears near caveat language that narrows the scope.",
                    repair_suggestion="Replace absolute wording with the exact domain, boundary condition, or exception class.",
                    confidence=0.68,
                    section=sentence.section,
                    trigger="absolute quantifier near caveat",
                    source_span=sentence.source_span,
                    related_source_span=caveats[0].source_span,
                )
            )
    return findings[:4]


def find_theory_as_fact_language(sentences: list[DocumentSentence]) -> list[Finding]:
    findings: list[Finding] = []
    for sentence in sentences:
        lower = sentence.text.lower()
        if is_tentative_language(lower):
            continue
        if any(re.search(pattern, lower) for pattern in THEORY_AS_FACT_PATTERNS):
            findings.append(
                Finding(
                    type="Theory-As-Fact Language",
                    severity="low",
                    sentence=trim_sentence(sentence.text),
                    explanation="The wording treats a model or theory as final authority rather than an evidenced framework.",
                    repair_suggestion="Use evidence-based phrasing and name which observations, assumptions, or tests support the statement.",
                    confidence=0.62,
                    section=sentence.section,
                    trigger="model authority phrasing",
                    source_span=sentence.source_span,
                )
            )
    return findings[:4]


def find_barrier_findings(claims: list[ClaimResult], sentences: list[DocumentSentence]) -> list[Finding]:
    findings: list[Finding] = []
    by_index = {sentence.index: sentence for sentence in sentences}
    for claim in claims:
        sentence = by_index.get(claim.sentence_index)
        section = sentence.section if sentence else claim.section
        severity = "medium" if claim.status == "failed" else "low"
        if "mechanism missing" in claim.gaps:
            findings.append(
                Finding(
                    type="Missing Mechanism Barrier",
                    severity=severity,
                    sentence=trim_sentence(claim.claim),
                    explanation="The claim names a resolution but does not explain the process that performs the resolution.",
                    repair_suggestion="Add a named mechanism, equation, causal pathway, proof step, or operational process.",
                    confidence=0.74 if severity == "medium" else 0.58,
                    section=section,
                    trigger="claim rubric gap",
                    claim_id=claim.id,
                    source_span=claim.source_span,
                )
            )
        if "evidence not linked" in claim.gaps:
            findings.append(
                Finding(
                    type="Evidence Gap",
                    severity=severity,
                    sentence=trim_sentence(claim.claim),
                    explanation="The claim does not link to nearby quantitative, citation, method, or proof evidence.",
                    repair_suggestion="Attach the claim to a citation, measurement, derivation, test, or falsifiable prediction.",
                    confidence=0.70 if severity == "medium" else 0.55,
                    section=section,
                    trigger="claim rubric gap",
                    claim_id=claim.id,
                    source_span=claim.source_span,
                )
            )
        lower_claim = claim.claim.lower()
        if (
            claim.status == "failed"
            and any(indicator in lower_claim for indicator in RESOLUTION_INDICATORS)
            and not is_tentative_language(lower_claim)
            and not is_background_context(lower_claim)
        ):
            findings.append(
                Finding(
                    type="Unsupported Resolution Claim",
                    severity="medium",
                    sentence=trim_sentence(claim.claim),
                    explanation="The paper appears to claim a resolution, but the rule audit did not find enough mechanism or evidence support.",
                    repair_suggestion="Restate the exact problem, then show the resolving mechanism and the evidence that would fail if the claim were wrong.",
                    confidence=0.76,
                    section=section,
                    trigger="failed resolution claim",
                    claim_id=claim.id,
                    source_span=claim.source_span,
                )
            )
    return findings[:10]


def assign_finding_ids(findings: list[Finding]) -> list[Finding]:
    assigned: list[Finding] = []
    for index, finding in enumerate(findings, start=1):
        if finding.id:
            assigned.append(finding)
            continue
        assigned.append(
            Finding(
                type=finding.type,
                severity=finding.severity,
                sentence=finding.sentence,
                explanation=finding.explanation,
                repair_suggestion=finding.repair_suggestion,
                confidence=finding.confidence,
                related_sentence=finding.related_sentence,
                id=f"F{index}",
                section=finding.section,
                trigger=finding.trigger,
                claim_id=finding.claim_id,
                source_span=finding.source_span,
                related_source_span=finding.related_source_span,
            )
        )
    return assigned


def determine_verdict(claims: list[ClaimResult], findings: list[Finding], evidence: EvidenceProfile) -> Verdict:
    if not claims:
        return "FAILS"
    high_findings = sum(1 for finding in findings if finding.severity == "high")
    if high_findings > 0:
        return "CREATES_NEW_PARADOXES"
    resolution_ratio = resolution_ratio_for_claims(claims)
    medium_penalty = min(0.18, sum(1 for finding in findings if finding.severity == "medium") * 0.045)
    adjusted_evidence = max(0.0, evidence.score - medium_penalty)
    blocking_medium_types = {"Evidence Gap", "Missing Mechanism Barrier", "Unsupported Resolution Claim", "Scope Conflict"}
    has_blocking_medium = any(finding.severity == "medium" and finding.type in blocking_medium_types for finding in findings)
    if resolution_ratio >= 0.72 and adjusted_evidence >= 0.58 and evidence.linked_evidence > 0 and not has_blocking_medium:
        return "RESOLVES"
    if resolution_ratio >= 0.42 or adjusted_evidence >= 0.42:
        return "PARTIAL"
    return "FAILS"


def build_verdict_rubric(claims: list[ClaimResult], findings: list[Finding], evidence: EvidenceProfile) -> list[RubricScore]:
    claim_ratio = resolution_ratio_for_claims(claims)
    contradiction_score = clamp(1.0 - sum(0.28 if finding.severity == "high" else 0.12 if finding.severity == "medium" else 0.05 for finding in findings), 0.0, 1.0)
    evidence_score = evidence.score
    mechanism_score = (
        sum(1 for claim in claims if claim.mechanism == "provided") / len(claims)
        if claims
        else 0.0
    )
    return [
        RubricScore("Claim resolution", round(claim_ratio, 3), 0.36, "Resolved claims count fully; partial claims count halfway"),
        RubricScore("Evidence strength", round(evidence_score, 3), 0.28, "Document-level evidence markers plus linked, proximate evidence snippets"),
        RubricScore("Internal consistency", round(contradiction_score, 3), 0.24, "Penalizes high and medium contradiction/risk findings"),
        RubricScore("Mechanism coverage", round(mechanism_score, 3), 0.12, "Share of claims with explicit mechanism language"),
    ]


def resolution_ratio_for_claims(claims: list[ClaimResult]) -> float:
    if not claims:
        return 0.0
    return (
        sum(1 for claim in claims if claim.status == "resolved")
        + 0.5 * sum(1 for claim in claims if claim.status == "partial")
    ) / len(claims)


def calculate_confidence(
    claims: list[ClaimResult], findings: list[Finding], evidence: EvidenceProfile, verdict: Verdict
) -> float:
    if not claims:
        return 0.56
    average_claim_quality = sum(claim.quality for claim in claims) / len(claims)
    linked_ratio = sum(1 for claim in claims if claim.evidence_links) / len(claims)
    finding_penalty = min(0.24, len(findings) * 0.018 + sum(0.06 for finding in findings if finding.severity == "high"))
    verdict_bonus = 0.05 if verdict in {"RESOLVES", "CREATES_NEW_PARADOXES"} else 0.0
    confidence = 0.46 + average_claim_quality * 0.25 + evidence.score * 0.20 + linked_ratio * 0.08 + verdict_bonus - finding_penalty
    return round(clamp(confidence, 0.1, 0.95), 3)


def build_summary(
    verdict: Verdict, claims: list[ClaimResult], findings: list[Finding], evidence: EvidenceProfile
) -> str:
    if not claims:
        return (
            "The paper does not make enough explicit resolution claims for the deterministic rules to validate. "
            "Add clear claims that name the problem being solved, the mechanism, and the evidence."
        )
    if verdict == "CREATES_NEW_PARADOXES":
        return (
            "The paper makes analyzable claims, but the rule set found a high-severity contradiction or barrier. "
            "Resolve that conflict before treating the verdict as supportive."
        )
    if verdict == "RESOLVES":
        return (
            "The paper's main claims include mechanisms, linked evidence, and enough consistency to pass the v2 rule checks. "
            "Review the curtain-up audit before using this as a final review."
        )
    if verdict == "PARTIAL":
        return (
            "The paper has useful claim structure, but some mechanisms, evidence links, or scope boundaries remain thin. "
            "Strengthen the flagged claims before relying on the result."
        )
    return (
        "The paper makes claims, but the rules did not find enough mechanism and evidence support. "
        "The fastest improvement is to connect each claim to a concrete process, citation, calculation, or test."
    )


def build_report_audit_events(
    sections: list[DocumentSection],
    sentences: list[DocumentSentence],
    claims: list[ClaimResult],
    findings: list[Finding],
    evidence: EvidenceProfile,
    verdict: Verdict,
) -> list[AuditEvent]:
    return [
        AuditEvent("section parse", "complete", f"{len(sections)} sections detected"),
        AuditEvent("sentence parse", "complete", f"{len(sentences)} analyzable sentences detected"),
        AuditEvent("claim extraction", "complete", f"{len(claims)} resolution or theory claims detected"),
        AuditEvent("evidence linking", "complete", f"{evidence.linked_evidence} evidence snippets indexed", evidence.score),
        AuditEvent("false-positive guardrails", "complete", "Tentative, prior-work, scoped-limit, and reference-like guardrails applied"),
        AuditEvent("barrier scan", "complete", f"{len(findings)} contradiction or repair findings emitted"),
        AuditEvent("verdict", verdict, "Deterministic verdict selected from claim, evidence, and finding scores"),
    ]


def build_issue_brief(claims: list[ClaimResult], findings: list[Finding], evidence: EvidenceProfile, verdict: Verdict) -> str:
    lines = [
        f"Verdict: {verdict}",
        f"Evidence score: {evidence.score:.2f}",
        f"Claims: {len(claims)} total, {sum(1 for claim in claims if claim.status == 'resolved')} resolved, {sum(1 for claim in claims if claim.status == 'partial')} partial, {sum(1 for claim in claims if claim.status == 'failed')} failed.",
    ]
    if findings:
        lines.append("Top findings:")
        for finding in findings[:6]:
            target = f" linked to {finding.claim_id}" if finding.claim_id else ""
            lines.append(f"- {finding.id}: {finding.type} ({finding.severity}){target}: {finding.explanation}")
    weak_claims = [claim for claim in claims if claim.status != "resolved"]
    if weak_claims:
        lines.append("Claims needing repair:")
        for claim in weak_claims[:6]:
            gaps = ", ".join(claim.gaps) if claim.gaps else "general support gap"
            lines.append(f"- {claim.id}: {gaps}. {claim.repair_suggestion}")
    return "\n".join(lines)


def count_terms(text: str, terms: set[str]) -> int:
    return sum(text.count(term) for term in terms)


def count_citations(text: str) -> int:
    return len(
        re.findall(
            r"\([A-Z][A-Za-z-]+(?: et al\.)?,?\s+(?:18|19|20)\d{2}\)"
            r"|[A-Z][A-Za-z-]+(?: et al\.)?\s+\((?:18|19|20)\d{2}\)"
            r"|\[(?:\d+|[A-Z][A-Za-z]+\d*)\]",
            text,
        )
    )


def count_math_content(text: str) -> int:
    math_symbols = len(re.findall(r"(?:[A-Za-z]\s*=\s*[-+*/^A-Za-z0-9(). ]+)|[=<>+\-*/^~]", text))
    equation_words = len(re.findall(r"\b(equation|formula|derivation|proof|theorem|lemma|model)\b", text.lower()))
    return math_symbols + equation_words


def is_tentative_language(text: str) -> bool:
    lower = text.lower()
    if re.search(r"\b(may|might|could|possibly)\b.*\b(resolve|solve|explain|account for|reconcile|predict)\b", lower):
        return True
    return any(re.search(rf"\b{re.escape(marker)}\b", lower) for marker in TENTATIVE_MARKERS)


def is_background_context(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in BACKGROUND_MARKERS)


def is_scope_limitation_context(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in LIMITATION_MARKERS)


def is_scoped_universal(text: str) -> bool:
    lower = text.lower()
    if not re.search(r"\b(all|always|every|never|none|universal|in every case|without exception)\b", lower):
        return False
    return bool(
        re.search(r"\b(within|inside|under|only under|only within|limited to|scoped to)\b", lower)
        or "calibrated sample" in lower
    )


def is_scoped_exception_pair(first: str, second: str) -> bool:
    context = f"{first} {second}".lower()
    if not is_scope_limitation_context(context):
        return False
    return bool(re.search(r"\b(scope|boundary|outside|within|limited|only under|not apply|not tested)\b", context))


def is_reference_like_sentence(text: str) -> bool:
    lower = text.lower().strip()
    if not lower:
        return False
    if lower.startswith(("references", "bibliography", "works cited")):
        return True
    if any(indicator in lower for indicator in CLAIM_INDICATORS | RESOLUTION_INDICATORS | PROBLEM_INDICATORS):
        return False
    citation_count = count_citations(text)
    years = len(re.findall(r"\b(?:18|19|20)\d{2}\b", text))
    words = content_words(text)
    bibliographic_punctuation = lower.count(";") + lower.count(",") >= 3
    return (citation_count >= 2 and len(words) <= 18) or (years >= 2 and bibliographic_punctuation and len(words) <= 22)


def is_comparison_context(first: str, second: str) -> bool:
    context = f"{first} {second}".lower()
    if any(marker in context for marker in COMPARISON_MARKERS | BACKGROUND_MARKERS):
        return True
    return bool(
        re.search(r"\b(prior|previous|earlier|standard|conventional)\b", context)
        and re.search(r"\b(our|proposed|this paper|this framework|new model)\b", context)
    )



def severity_for_score(score: float) -> str:
    if score >= 0.82:
        return "high"
    if score >= 0.62:
        return "medium"
    return "low"


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def trim_sentence(sentence: str, limit: int = 260) -> str:
    sentence = sentence.strip()
    if len(sentence) <= limit:
        return sentence
    return sentence[: limit - 3].rstrip() + "..."


def repair_suggestion_for_gaps(gaps: list[str]) -> str:
    if not gaps:
        return "Keep the claim tied to its mechanism and evidence when revising."
    repairs = []
    if "mechanism missing" in gaps:
        repairs.append("name the mechanism that performs the resolution")
    if "evidence not linked" in gaps:
        repairs.append("attach a citation, measurement, derivation, or falsifiable test")
    if "details not specific" in gaps:
        repairs.append("add concrete conditions, examples, or boundary cases")
    if "problem scope unclear" in gaps:
        repairs.append("state the exact paradox or contradiction being resolved")
    return "To repair this claim, " + "; ".join(repairs) + "."


def dedupe_claim_candidates(candidates: list[ClaimCandidate]) -> list[ClaimCandidate]:
    seen: set[str] = set()
    deduped: list[ClaimCandidate] = []
    for candidate in candidates:
        key = re.sub(r"\W+", " ", candidate.sentence.text.lower()).strip()
        if key not in seen:
            seen.add(key)
            deduped.append(candidate)
    return deduped


def dedupe_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, str]] = set()
    deduped: list[Finding] = []
    for finding in findings:
        key = (finding.type, finding.sentence.lower())
        if key not in seen:
            seen.add(key)
            deduped.append(finding)
    return deduped


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        key = re.sub(r"\W+", " ", item.lower()).strip()
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def clamp(value: float, minimum: float, maximum: float) -> float:
    if math.isnan(value):
        return minimum
    return max(minimum, min(maximum, value))
