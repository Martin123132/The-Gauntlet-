from __future__ import annotations

from gauntlet_core.models import AnalysisReport, ClaimResult, EvidenceLink, EvidenceProfile, Finding, SourceSpan
from gauntlet_core.repair_workshop import build_repair_steps
from gauntlet_core.source_reader import build_source_reader_view, source_reader_to_markdown


def source_reader_fixture() -> AnalysisReport:
    spans = [
        SourceSpan("S1", "Abstract", 1, 1, 0, 80, "The paper resolves the paradox without explaining the mechanism."),
        SourceSpan("S2", "Claims", 2, 2, 81, 150, "The model says every signal is always conserved."),
        SourceSpan("S3", "Evidence", 3, 2, 151, 225, "Smith et al. (2024) report an unclear measurement."),
        SourceSpan("S4", "Appendix", 4, 4, 226, 310, "UNREFERENCED FULL PAPER TEXT SHOULD NOT APPEAR."),
    ]
    return AnalysisReport(
        source_name="source-reader-paper.txt",
        verdict="FAILS",
        confidence=0.42,
        created_at="2026-05-20T00:00:00+00:00",
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
        summary="Fixture report for source reader.",
        source_spans=spans,
    )


def test_source_reader_selects_default_anchor_and_context():
    report = source_reader_fixture()
    view = build_source_reader_view(report)

    assert view.selected_anchor == "S1"
    assert view.selected_span is not None
    assert [span.anchor_id for span in view.context_spans] == ["S1", "S2", "S3"]
    assert view.matching_anchors[0].anchor_id == "S1"


def test_source_reader_search_and_filters_match_source_spans():
    report = source_reader_fixture()
    view = build_source_reader_view(report, query="unclear measurement", filters={"section": "Evidence", "page": 2})

    assert view.selected_anchor == "S3"
    assert [anchor.anchor_id for anchor in view.matching_anchors] == ["S3"]
    assert view.section_filter == "Evidence"
    assert view.page_filter == 2


def test_source_reader_search_can_return_no_matches_without_losing_context():
    report = source_reader_fixture()
    view = build_source_reader_view(report, query="not present anywhere")

    assert view.selected_anchor == "S1"
    assert view.matching_anchors == []
    assert view.context_spans


def test_source_reader_related_items_include_audit_and_revision_rechecks():
    report = source_reader_fixture()
    steps = build_repair_steps(report)
    anchored_step = next(step for step in steps if step.source_span)
    view = build_source_reader_view(
        report,
        selected_anchor=anchored_step.source_span.anchor_id,
        filters={
            "revision_rechecks": {
                anchored_step.id: {
                    "id": "VTEST",
                    "step_id": anchored_step.id,
                    "status": "improved",
                    "summary": "The revision improves the mechanism support.",
                }
            }
        },
    )

    kinds = {item.kind for item in view.related_items}

    assert "Claim" in kinds
    assert "Repair" in kinds
    assert "Revision Re-Check" in kinds


def test_source_reader_markdown_exports_selected_snippets_not_full_paper_text():
    report = source_reader_fixture()
    view = build_source_reader_view(report, selected_anchor="S1")
    markdown = source_reader_to_markdown(report, view)

    assert "# Source Reader: source-reader-paper.txt" in markdown
    assert "Selected Source" in markdown
    assert "Page 1, Abstract, sentence 1" in markdown
    assert "Add the missing mechanism and link it to evidence." in markdown
    assert "UNREFERENCED FULL PAPER TEXT SHOULD NOT APPEAR" not in markdown
    assert "do not include the full uploaded paper file" in markdown
