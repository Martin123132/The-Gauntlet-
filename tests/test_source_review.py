from __future__ import annotations

from gauntlet_core.models import AnalysisReport, ClaimResult, EvidenceLink, EvidenceProfile, Finding, SourceSpan
from gauntlet_core.source_review import build_source_review_items, source_review_to_markdown


def source_review_fixture() -> AnalysisReport:
    spans = [
        SourceSpan("S1", "Abstract", 1, 2, 0, 60, "The paper resolves the paradox without explaining the mechanism."),
        SourceSpan("S2", "Claims", 2, 2, 61, 130, "The model says every signal is always conserved."),
        SourceSpan("S3", "Evidence", 3, 2, 131, 205, "Smith et al. (2024) report an unclear measurement."),
        SourceSpan("S4", "Appendix", 4, 2, 206, 280, "UNREFERENCED FULL PAPER TEXT SHOULD NOT APPEAR."),
    ]
    return AnalysisReport(
        source_name="source-review-paper.txt",
        verdict="FAILS",
        confidence=0.42,
        created_at="2026-05-19T00:00:00+00:00",
        word_count=42,
        sentence_count=4,
        claims=[
            ClaimResult(
                claim="The paper resolves the paradox without explaining the mechanism.",
                status="failed",
                quality=0.2,
                mechanism="",
                evidence_strength=0.1,
                gaps=["mechanism missing", "evidence not linked"],
                id="C1",
                source_span=spans[0],
                repair_suggestion="Add the missing mechanism and link it to evidence.",
            ),
            ClaimResult(
                claim="The model says every signal is always conserved.",
                status="partial",
                quality=0.45,
                mechanism="model assertion",
                evidence_strength=0.25,
                gaps=["details not specific"],
                id="C2",
                source_span=spans[1],
                repair_suggestion="Add scope boundaries and falsifiable conditions.",
            ),
        ],
        findings=[
            Finding(
                type="Theory-As-Fact Language",
                severity="high",
                sentence="The model says every signal is always conserved.",
                explanation="Model authority is presented as settled fact.",
                repair_suggestion="Reword as a hypothesis and attach evidence.",
                confidence=0.9,
                id="F1",
                source_span=spans[1],
            )
        ],
        evidence=EvidenceProfile(
            score=0.24,
            quantitative_evidence=1,
            mathematical_content=0,
            citations=1,
            methodology_terms=0,
            evidence_terms=1,
            linked_evidence=2,
            evidence_links=[
                EvidenceLink("E1", "citation", "Smith et al. (2024) report an unclear measurement.", "Evidence", 3, 0.45, spans[2]),
                EvidenceLink("E2", "support", "The model says every signal is always conserved.", "Claims", 2, 0.8, spans[1]),
            ],
        ),
        summary="Fixture report for source review.",
        source_spans=spans,
    )


def test_source_review_items_include_queue_inputs_and_priority_order():
    report = source_review_fixture()
    items = build_source_review_items(report)
    kinds = {item.kind for item in items}

    assert {"Finding", "Claim", "Evidence", "Repair"}.issubset(kinds)
    assert [item.priority for item in items] == sorted(item.priority for item in items)

    high_finding_index = next(index for index, item in enumerate(items) if item.kind == "Finding" and item.severity == "high")
    failed_claim_index = next(index for index, item in enumerate(items) if item.kind == "Claim" and item.status == "failed")
    partial_claim_index = next(index for index, item in enumerate(items) if item.kind == "Claim" and item.status == "partial")
    weak_evidence_index = next(index for index, item in enumerate(items) if item.kind == "Evidence" and item.status == "weak")
    supporting_index = next(index for index, item in enumerate(items) if item.kind == "Evidence" and item.status == "supporting")

    assert high_finding_index < failed_claim_index < partial_claim_index < weak_evidence_index < supporting_index


def test_source_review_markdown_contains_snippets_not_full_paper_text():
    report = source_review_fixture()
    markdown = source_review_to_markdown(report)

    assert "# Source Review: source-review-paper.txt" in markdown
    assert "Theory-As-Fact Language" in markdown
    assert "Page 2, Claims, sentence 2" in markdown
    assert "Reword as a hypothesis and attach evidence." in markdown
    assert "UNREFERENCED FULL PAPER TEXT SHOULD NOT APPEAR" not in markdown
