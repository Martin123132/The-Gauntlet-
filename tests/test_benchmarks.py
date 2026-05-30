from gauntlet_core import analyze_paper_text
from gauntlet_core.benchmarks import (
    BenchmarkSample,
    compare_report_to_sample,
    list_benchmark_samples,
    run_benchmark_sample,
    run_calibration_suite,
)


def test_all_benchmark_samples_pass_expected_behavior():
    results = [run_benchmark_sample(sample.id) for sample in list_benchmark_samples()]

    assert len(results) >= 28
    assert all(result.passed for result in results)
    assert all(result.score == 1.0 for result in results)


def test_benchmark_metadata_is_public_and_explanatory():
    for sample in list_benchmark_samples():
        assert sample.id
        assert sample.title
        assert sample.category
        assert sample.paper_text.strip()
        assert sample.expected_verdict in {"RESOLVES", "PARTIAL", "FAILS", "CREATES_NEW_PARADOXES"}
        assert isinstance(sample.expected_absent_findings, tuple)
        assert isinstance(sample.expected_absent_claim_gaps, tuple)
        assert len(sample.why_it_matters) > 40


def test_benchmark_comparison_reports_misses_and_extras():
    sample = BenchmarkSample(
        id="comparison-smoke",
        title="Comparison Smoke",
        category="Test",
        paper_text="The paper resolves the paradox and eliminates the contradiction.",
        expected_verdict="RESOLVES",
        expected_findings=("Temporal Conflict",),
        expected_claim_gaps=("mechanism missing",),
        why_it_matters="Synthetic comparison fixture for checking miss and extra reporting.",
    )
    report = analyze_paper_text(sample.paper_text)

    comparison = compare_report_to_sample(sample, report)

    assert not comparison.passed
    assert not comparison.verdict_match
    assert comparison.missed_findings == ("Temporal Conflict",)
    assert "mechanism missing" in comparison.matched_claim_gaps
    assert "Evidence Gap" in comparison.extra_findings
    assert comparison.absent_findings_kept_out == ()
    assert comparison.unexpected_absent_findings == ()


def test_clean_benchmark_case_fails_when_extra_findings_appear():
    sample = next(sample for sample in list_benchmark_samples() if sample.id == "strong-mechanism-evidence")
    report = analyze_paper_text("The paper resolves the paradox and eliminates the contradiction.")
    comparison = compare_report_to_sample(sample, report)

    assert comparison.extra_findings
    assert not comparison.passed


def test_absent_guardrails_fail_when_unwanted_findings_appear():
    sample = BenchmarkSample(
        id="absent-guardrail-smoke",
        title="Absent Guardrail Smoke",
        category="Test",
        paper_text="The paper resolves the paradox and eliminates the contradiction.",
        expected_verdict="FAILS",
        expected_findings=("Unsupported Resolution Claim",),
        expected_claim_gaps=("mechanism missing",),
        expected_absent_findings=("Evidence Gap",),
        expected_absent_claim_gaps=("details not specific",),
        why_it_matters="Synthetic comparison fixture for checking false-positive guardrail reporting in benchmark comparisons.",
    )
    report = analyze_paper_text(sample.paper_text)

    comparison = compare_report_to_sample(sample, report)

    assert "Evidence Gap" in comparison.unexpected_absent_findings
    assert "details not specific" in comparison.unexpected_absent_claim_gaps
    assert not comparison.passed


def test_benchmark_export_distinguishes_match_from_paper_pass():
    comparison = run_benchmark_sample("weak-evidence")
    markdown = comparison.to_markdown()

    assert comparison.report.verdict == "PARTIAL"
    assert "Benchmark result: **EXPECTED MATCH**" in markdown
    assert "False-Positive Guardrails" in markdown
    assert "Result: **PASS**" not in markdown


def test_calibration_suite_summarizes_full_benchmark_corpus():
    result = run_calibration_suite()

    assert result.sample_count >= 28
    assert result.pass_rate == 1.0
    assert result.verdict_match_rate == 1.0
    assert result.guardrail_pass_rate == 1.0
    assert result.failing_sample_ids == ()
    assert {summary.category for summary in result.category_summaries} >= {
        "False-positive guard",
        "Positive control",
    }


def test_calibration_exports_include_metrics_and_category_detail():
    result = run_calibration_suite()
    data = result.to_json()
    markdown = result.to_markdown()

    assert '"sample_count":' in data
    assert '"guardrail_pass_rate": 1.0' in data
    assert "The Gauntlet Calibration Suite" in markdown
    assert "Overall pass rate: 100%" in markdown
    assert "Category Calibration" in markdown
    assert "False-positive guard" in markdown
    assert "## Failing Cases" in markdown
