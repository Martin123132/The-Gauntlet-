from __future__ import annotations

import math
import re

from .contradiction import ClaimPair, ContradictionEngine, content_words, has_negation
from .models import AnalysisReport, ClaimResult, EvidenceProfile, Finding, Verdict, utc_now_iso


CLAIM_INDICATORS = {
    "resolves",
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
    "therefore",
    "thus",
    "consequently",
    "because",
    "due to",
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
}

DETAIL_INDICATORS = {
    "specifically",
    "precisely",
    "for example",
    "such as",
    "including",
    "namely",
    "i.e.",
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


def analyze_paper_text(text: str, source_name: str = "uploaded document") -> AnalysisReport:
    cleaned_text = normalize_document_text(text)
    sentences = split_sentences(cleaned_text)
    evidence = assess_evidence(cleaned_text)
    claims = analyze_claims(extract_claims(sentences))
    findings = find_internal_contradictions(sentences)
    verdict = determine_verdict(claims, findings, evidence)
    confidence = calculate_confidence(claims, findings, evidence, verdict)
    summary = build_summary(verdict, claims, findings, evidence)
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
    )


def normalize_document_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if len(part.strip()) >= 20]


def extract_claims(sentences: list[str], limit: int = 24) -> list[str]:
    claims: list[str] = []
    for sentence in sentences:
        lower = sentence.lower()
        if any(indicator in lower for indicator in CLAIM_INDICATORS):
            claims.append(sentence)
            continue
        if any(problem in lower for problem in PROBLEM_INDICATORS) and any(
            word in lower for word in ["model", "framework", "theory", "paper", "approach"]
        ):
            claims.append(sentence)
    return dedupe_preserve_order(claims)[:limit]


def analyze_claims(claims: list[str]) -> list[ClaimResult]:
    results: list[ClaimResult] = []
    for claim in claims:
        lower = claim.lower()
        has_mechanism = any(indicator in lower for indicator in MECHANISM_INDICATORS)
        has_detail = any(indicator in lower for indicator in DETAIL_INDICATORS)
        evidence_hits = count_terms(lower, EVIDENCE_TERMS)
        methodology_hits = count_terms(lower, METHODOLOGY_TERMS)
        number_hits = len(re.findall(r"\d+(?:\.\d+)?%?", claim))
        citation_hits = count_citations(claim)
        equation_hits = count_math_content(claim)

        mechanism_score = 0.32 if has_mechanism else 0.0
        detail_score = 0.12 if has_detail else 0.0
        evidence_score = min(0.36, (evidence_hits + methodology_hits) * 0.06 + number_hits * 0.05 + citation_hits * 0.08)
        math_score = min(0.2, equation_hits * 0.08)
        quality = clamp(0.12 + mechanism_score + detail_score + evidence_score + math_score, 0.05, 0.98)

        gaps: list[str] = []
        if not has_mechanism:
            gaps.append("mechanism missing")
        if evidence_hits + methodology_hits + number_hits + citation_hits == 0:
            gaps.append("evidence thin")
        if not has_detail:
            gaps.append("details not specific")

        if quality >= 0.72 and has_mechanism and "evidence thin" not in gaps:
            status = "resolved"
        elif quality >= 0.38 or has_mechanism:
            status = "partial"
        else:
            status = "failed"

        results.append(
            ClaimResult(
                claim=claim,
                status=status,
                quality=round(quality, 3),
                mechanism="provided" if has_mechanism else "missing",
                evidence_strength=round(clamp(evidence_score + math_score + citation_hits * 0.05, 0.0, 0.95), 3),
                gaps=gaps,
            )
        )
    return results


def assess_evidence(text: str) -> EvidenceProfile:
    lower = text.lower()
    quantitative = len(re.findall(r"\b\d+(?:\.\d+)?%?\b|r\^?2\s*=|rmse\s*=|p\s*[<=>]", lower))
    math_content = count_math_content(text)
    citations = count_citations(text)
    methodology = count_terms(lower, METHODOLOGY_TERMS)
    evidence_terms = count_terms(lower, EVIDENCE_TERMS)
    score = (
        0.16
        + 0.28 * min(1.0, quantitative / 8)
        + 0.24 * min(1.0, math_content / 6)
        + 0.22 * min(1.0, citations / 6)
        + 0.16 * min(1.0, methodology / 8)
        + 0.10 * min(1.0, evidence_terms / 10)
    )
    return EvidenceProfile(
        score=round(clamp(score, 0.0, 0.98), 3),
        quantitative_evidence=quantitative,
        mathematical_content=math_content,
        citations=citations,
        methodology_terms=methodology,
        evidence_terms=evidence_terms,
    )


def find_internal_contradictions(sentences: list[str]) -> list[Finding]:
    engine = ContradictionEngine()
    findings: list[Finding] = []
    max_pairs = 360
    checked = 0
    for i, first in enumerate(sentences):
        for j, second in enumerate(sentences[i + 1 :], i + 1):
            if checked >= max_pairs:
                break
            checked += 1
            if is_comparison_context(first, second):
                continue
            first_words = content_words(first)
            second_words = content_words(second)
            overlap = jaccard(first_words, second_words)
            if overlap < 0.22:
                continue
            contradiction = engine.detect(ClaimPair(f"s{i + 1}-s{j + 1}", first, second))
            if contradiction:
                findings.append(
                    Finding(
                        type=contradiction.type.value.replace("_", " ").title(),
                        severity=severity_for_score(contradiction.score),
                        sentence=trim_sentence(second),
                        related_sentence=trim_sentence(first),
                        explanation=contradiction.note,
                        repair_suggestion=contradiction.repair_suggestion,
                        confidence=round(contradiction.score, 2),
                    )
                )
            elif has_negation(first) != has_negation(second) and overlap >= 0.42:
                findings.append(
                    Finding(
                        type="Potential Direct Negation",
                        severity="medium",
                        sentence=trim_sentence(second),
                        related_sentence=trim_sentence(first),
                        explanation="Two similar sentences appear to differ mainly by negation.",
                        repair_suggestion="Clarify whether these sentences refer to different scopes, dates, or assumptions.",
                        confidence=round(overlap, 2),
                    )
                )
        if checked >= max_pairs:
            break

    findings.extend(find_circular_reasoning(sentences))
    return dedupe_findings(findings)[:12]


def find_circular_reasoning(sentences: list[str]) -> list[Finding]:
    because_sentences = [sentence for sentence in sentences if "because" in sentence.lower()]
    therefore_sentences = [sentence for sentence in sentences if "therefore" in sentence.lower()]
    if len(because_sentences) >= 2 and len(therefore_sentences) >= 2:
        return [
            Finding(
                type="Potential Circular Reasoning",
                severity="low",
                sentence=trim_sentence(because_sentences[0]),
                related_sentence=trim_sentence(therefore_sentences[0]),
                explanation="The paper contains repeated because/therefore reasoning that should be checked for circular support.",
                repair_suggestion="Make premises, evidence, and conclusions explicit so the conclusion is not used as its own support.",
                confidence=0.45,
            )
        ]
    return []


def determine_verdict(claims: list[ClaimResult], findings: list[Finding], evidence: EvidenceProfile) -> Verdict:
    if not claims:
        return "FAILS"
    high_findings = sum(1 for finding in findings if finding.severity == "high")
    if high_findings > 0:
        return "CREATES_NEW_PARADOXES"
    resolution_ratio = (
        sum(1 for claim in claims if claim.status == "resolved")
        + 0.5 * sum(1 for claim in claims if claim.status == "partial")
    ) / max(1, len(claims))
    if resolution_ratio >= 0.72 and evidence.score >= 0.58:
        return "RESOLVES"
    if resolution_ratio >= 0.42 or evidence.score >= 0.42:
        return "PARTIAL"
    return "FAILS"


def calculate_confidence(
    claims: list[ClaimResult], findings: list[Finding], evidence: EvidenceProfile, verdict: Verdict
) -> float:
    if not claims:
        return 0.56
    average_claim_quality = sum(claim.quality for claim in claims) / len(claims)
    finding_penalty = min(0.22, len(findings) * 0.025 + sum(0.05 for finding in findings if finding.severity == "high"))
    verdict_bonus = 0.06 if verdict in {"RESOLVES", "CREATES_NEW_PARADOXES"} else 0.0
    confidence = 0.48 + average_claim_quality * 0.26 + evidence.score * 0.22 + verdict_bonus - finding_penalty
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
            "The paper makes analyzable claims, but the rule set found a high-severity internal contradiction. "
            "Resolve that conflict before treating the verdict as supportive."
        )
    if verdict == "RESOLVES":
        return (
            "The paper's main claims include mechanisms and enough evidence markers to pass the v1 rule checks. "
            "Review the claim list and evidence profile before using this as a final review."
        )
    if verdict == "PARTIAL":
        return (
            "The paper has some usable claim structure, but at least part of the mechanism or evidence trail is thin. "
            "Strengthen the flagged claims before relying on the result."
        )
    return (
        "The paper makes claims, but the rules did not find enough mechanism and evidence support. "
        "The fastest improvement is to connect each claim to a concrete process, citation, calculation, or test."
    )


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
    math_symbols = len(re.findall(r"[=<>∫∂∇Σ∝≈≠≤≥±]", text))
    equation_words = len(re.findall(r"\b(equation|formula|derivation|proof|theorem|model)\b", text.lower()))
    return math_symbols + equation_words


def is_comparison_context(first: str, second: str) -> bool:
    context = f"{first} {second}".lower()
    return any(marker in context for marker in COMPARISON_MARKERS)


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


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        key = re.sub(r"\W+", " ", item.lower()).strip()
        if key not in seen:
            seen.add(key)
            deduped.append(item)
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


def clamp(value: float, minimum: float, maximum: float) -> float:
    if math.isnan(value):
        return minimum
    return max(minimum, min(maximum, value))
