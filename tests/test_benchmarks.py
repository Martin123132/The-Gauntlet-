from gauntlet_core import analyze_paper_text
from gauntlet_core.benchmarks import BenchmarkSample, compare_report_to_sample, list_benchmark_samples, run_benchmark_sample


def test_all_benchmark_samples_pass_expected_behavior():
    results = [run_benchmark_sample(sample.id) for sample in list_benchmark_samples()]

    assert len(results) >= 8
    assert all(result.passed for result in results)
    assert all(result.score == 1.0 for result in results)


def test_benchmark_metadata_is_public_and_explanatory():
    for sample in list_benchmark_samples():
        assert sample.id
        assert sample.title
        assert sample.category
        assert sample.paper_text.strip()
        assert sample.expected_verdict in {"RESOLVES", "PARTIAL", "FAILS", "CREATES_NEW_PARADOXES"}
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


def test_clean_benchmark_case_fails_when_extra_findings_appear():
    sample = next(sample for sample in list_benchmark_samples() if sample.id == "strong-mechanism-evidence")
    report = analyze_paper_text("The paper resolves the paradox and eliminates the contradiction.")
    comparison = compare_report_to_sample(sample, report)

    assert comparison.extra_findings
    assert not comparison.passed


def test_benchmark_export_distinguishes_match_from_paper_pass():
    comparison = run_benchmark_sample("weak-evidence")
    markdown = comparison.to_markdown()

    assert comparison.report.verdict == "PARTIAL"
    assert "Benchmark result: **EXPECTED MATCH**" in markdown
    assert "Result: **PASS**" not in markdown
