from gauntlet_core import analyze_paper_text


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
