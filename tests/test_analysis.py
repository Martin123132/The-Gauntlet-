import json

from gauntlet_core import SourceSpan, analyze_paper_text
from gauntlet_core.analysis import parse_document_sections


def test_no_clear_claims_fails():
    report = analyze_paper_text("This short note describes a topic without making a resolution claim.")

    assert report.verdict == "FAILS"
    assert report.claims == []
    assert "does not make enough explicit resolution claims" in report.summary


def test_strong_mechanism_and_evidence_resolves():
    text = """
    The framework resolves the anomaly through a geometric mechanism that predicts
    the measured curve by 14.2 percent. The paper explains the discrepancy using
    equation y = mx + b and compares the result against three observational
    datasets. Smith et al. (2021) and Jones (2023) report measurements that support
    the same prediction with RMSE = 0.03.
    """

    report = analyze_paper_text(text)

    assert report.verdict == "RESOLVES"
    assert report.evidence.score >= 0.58
    assert report.resolved_claims >= 1


def test_weak_evidence_is_partial_or_fails():
    text = "The theory explains the problem because the model says it does."

    report = analyze_paper_text(text)

    assert report.verdict in {"PARTIAL", "FAILS"}
    assert report.evidence.score < 0.3


def test_internal_contradiction_creates_new_paradoxes():
    text = """
    The framework resolves the contradiction because the model provides a mechanism
    and equation x = 1 with data from Smith et al. (2021). The framework states the
    signal is always constant in 1990. The framework states the signal changed in
    2020 after the same measurement process.
    """

    report = analyze_paper_text(text)

    assert report.verdict == "CREATES_NEW_PARADOXES"
    assert any(finding.severity == "high" for finding in report.findings)


def test_resolution_claim_without_mechanism_has_gap():
    text = "The paper resolves the paradox and solves the anomaly."

    report = analyze_paper_text(text)

    assert report.claims
    assert "mechanism missing" in report.claims[0].gaps


def test_section_parsing_and_evidence_links_are_visible():
    text = """
    Abstract
    The framework resolves the paradox because its mechanism separates local and global cases.
    Evidence
    Smith et al. (2024) reports 12 measurements and equation x = 2 supporting the prediction.
    Conclusion
    Therefore the paper explains the anomaly through a bounded process.
    """

    sections = parse_document_sections(text)
    report = analyze_paper_text(text)

    assert [section.title for section in sections] == ["Abstract", "Evidence", "Conclusion"]
    assert report.sections == ["Abstract", "Evidence", "Conclusion"]
    assert report.evidence.evidence_links
    assert any(claim.evidence_links for claim in report.claims)
    assert report.verdict_rubric
    assert report.audit_events
    assert report.source_spans
    assert all(claim.source_span for claim in report.claims)
    assert all(link.source_span for link in report.evidence.evidence_links)


def test_scope_conflict_and_theory_as_fact_are_flagged():
    text = """
    The theory proves that the paradox is impossible because the model says that every signal is always conserved.
    However, under boundary cases the signal can change when the sampling frame changes.
    """

    report = analyze_paper_text(text)
    finding_types = {finding.type for finding in report.findings}

    assert "Scope Conflict" in finding_types
    assert "Theory-As-Fact Language" in finding_types


def test_unsupported_resolution_claim_emits_barrier_findings():
    report = analyze_paper_text("The paper resolves the paradox and eliminates the contradiction.")

    finding_types = {finding.type for finding in report.findings}

    assert "Missing Mechanism Barrier" in finding_types
    assert "Evidence Gap" in finding_types
    assert "Unsupported Resolution Claim" in finding_types


def test_tentative_hypothesis_is_not_full_resolution_or_unsupported_claim():
    text = """
    We hypothesize that the framework may explain the anomaly if a boundary condition changes the sampling process.
    This is a tentative proposal rather than a completed resolution, and it still requires a direct test.
    """

    report = analyze_paper_text(text)
    finding_types = {finding.type for finding in report.findings}

    assert report.verdict != "RESOLVES"
    assert "Unsupported Resolution Claim" not in finding_types
    assert "Theory-As-Fact Language" not in finding_types


def test_scoped_limitation_is_not_scope_conflict():
    text = """
    The framework explains the anomaly through a sampling process under low-energy boundary conditions.
    The claim is limited to the calibrated sample and does not apply outside that scope.
    """

    report = analyze_paper_text(text)

    assert "Scope Conflict" not in {finding.type for finding in report.findings}


def test_prior_work_comparison_is_not_internal_contradiction():
    text = """
    Prior work claimed the signal was always constant in every measurement.
    Unlike the conventional model, this framework explains the anomaly through a boundary process where the signal changes after calibration.
    """

    report = analyze_paper_text(text)
    finding_types = {finding.type for finding in report.findings}

    assert "Temporal Conflict" not in finding_types
    assert "Potential Direct Negation" not in finding_types
    assert "Property Mismatch" not in finding_types


def test_unlinked_citations_and_equations_do_not_resolve():
    text = """
    References
    Smith et al. (2021), Journal of Tests, 14, 22-31; Jones (2023), Methods Review, 9, 100-118.
    Methods
    Equation x = y + 2. RMSE = 0.04. R2 = 0.91.
    No interpretation or resolution claim is provided.
    """

    report = analyze_paper_text(text)

    assert report.verdict == "FAILS"
    assert report.resolved_claims == 0


def test_assertive_model_authority_still_flags_theory_as_fact():
    text = """
    The model proves that the paradox is impossible because the theory dictates that all violations are forbidden.
    The framework explains the anomaly through a formal mechanism, but it gives no measurement or test.
    """

    report = analyze_paper_text(text)

    assert "Theory-As-Fact Language" in {finding.type for finding in report.findings}


def test_source_spans_attach_to_claims_findings_and_exports():
    text = (
        "The paper resolves the paradox because the mechanism is measured by 12 tests. "
        "The model says every signal is always conserved. However, under boundary cases the signal can change."
    )
    source_spans = [
        SourceSpan("S1", "Document", 1, 3, 0, 72, "The paper resolves the paradox because the mechanism is measured by 12 tests."),
        SourceSpan("S2", "Document", 2, 3, 73, 123, "The model says every signal is always conserved."),
        SourceSpan("S3", "Document", 3, 3, 124, 181, "However, under boundary cases the signal can change."),
    ]

    report = analyze_paper_text(text, source_name="paper.pdf", source_spans=source_spans)
    data = json.loads(report.to_json())
    markdown = report.to_markdown()

    assert report.source_spans[0].page_number == 3
    assert report.claims[0].source_span is not None
    assert all(finding.source_span for finding in report.findings)
    assert data["claims"][0]["source_span"]["page_number"] == 3
    assert "Page 3" in markdown
    assert "Source Trace" in markdown


def test_source_spans_degrade_without_page_numbers():
    report = analyze_paper_text("The paper resolves the paradox because the mechanism is measured by 12 tests.")

    assert report.source_spans
    assert report.source_spans[0].page_number is None
    assert "Document, sentence 1" in report.to_markdown()
