from __future__ import annotations

from gauntlet_core.evidence_map import build_claim_evidence_map, claim_evidence_map_to_markdown
from gauntlet_core.models import AnalysisReport, ClaimResult, EvidenceLink, EvidenceProfile, SourceSpan


def evidence_map_fixture() -> AnalysisReport:
    spans = [
        SourceSpan("S1", "Claims", 1, None, 0, 80, "The paper resolves the paradox without linked evidence."),
        SourceSpan("S2", "Claims", 2, None, 81, 170, "The framework explains the anomaly using measured curvature."),
        SourceSpan("S3", "Evidence", 3, None, 171, 260, "Smith et al. (2024) report 42 measured curvature observations."),
        SourceSpan("S4", "Evidence", 4, None, 261, 340, "A separate appendix equation is not tied to a claim."),
    ]
    linked = EvidenceLink("E1", "citation", spans[2].text, "Evidence", 3, 0.72, spans[2])
    orphan = EvidenceLink("E2", "math", spans[3].text, "Evidence", 4, 0.68, spans[3])
    return AnalysisReport(
        source_name="evidence-map.txt",
        verdict="PARTIAL",
        confidence=0.62,
        created_at="2026-05-21T00:00:00+00:00",
        word_count=56,
        sentence_count=4,
        claims=[
            ClaimResult(
                claim=spans[0].text,
                status="failed",
                quality=0.22,
                mechanism="",
                evidence_strength=0.0,
                gaps=["evidence not linked", "mechanism missing"],
                id="C1",
                source_span=spans[0],
            ),
            ClaimResult(
                claim=spans[1].text,
                status="resolved",
                quality=0.78,
                mechanism="provided",
                evidence_strength=0.65,
                gaps=[],
                id="C2",
                source_span=spans[1],
                evidence_links=[linked],
            ),
        ],
        findings=[],
        evidence=EvidenceProfile(
            score=0.58,
            quantitative_evidence=1,
            mathematical_content=1,
            citations=1,
            methodology_terms=0,
            evidence_terms=1,
            linked_evidence=2,
            evidence_links=[linked, orphan],
        ),
        summary="Fixture report for claim-evidence mapping.",
        source_spans=spans,
    )


def test_claim_evidence_map_counts_missing_strong_and_orphan_links():
    report = evidence_map_fixture()
    evidence_map = build_claim_evidence_map(report)

    assert len(evidence_map.rows) == 2
    assert evidence_map.claims_with_evidence == 1
    assert evidence_map.claims_with_usable_evidence == 1
    assert evidence_map.claims_with_strong_evidence == 1
    assert [row.claim_id for row in evidence_map.rows] == ["C1", "C2"]
    assert evidence_map.rows[0].coverage == "missing"
    assert evidence_map.rows[0].priority == "high"
    assert evidence_map.rows[1].coverage == "strong"
    assert [link.id for link in evidence_map.orphan_evidence_links] == ["E2"]


def test_claim_evidence_map_markdown_contains_refs_and_privacy_note():
    report = evidence_map_fixture()
    markdown = claim_evidence_map_to_markdown(report)

    assert "# Claim-Evidence Map: evidence-map.txt" in markdown
    assert "C1 - Missing" in markdown
    assert "C2 - Strong" in markdown
    assert "Orphan Evidence" in markdown
    assert "Smith et al. (2024)" in markdown
    assert "do not include the full uploaded paper file" in markdown


def test_claim_evidence_map_handles_no_claims():
    report = evidence_map_fixture()
    empty_report = AnalysisReport(
        source_name="empty.txt",
        verdict="FAILS",
        confidence=0.1,
        created_at=report.created_at,
        word_count=0,
        sentence_count=0,
        claims=[],
        findings=[],
        evidence=report.evidence,
        summary="No claims.",
    )

    evidence_map = build_claim_evidence_map(empty_report)
    markdown = claim_evidence_map_to_markdown(empty_report, evidence_map)

    assert evidence_map.rows == ()
    assert "No clear claims were detected" in markdown
