from pathlib import Path
import json

import pytest

from gauntlet_core import analyze_paper_text
from gauntlet_core.benchmarks import (
    BenchmarkSample,
    CALIBRATION_VERSION,
    evaluate_calibration_gate,
    compare_report_to_sample,
    list_benchmark_samples,
    run_benchmark_sample,
    run_calibration_suite,
)


def test_all_benchmark_samples_pass_expected_behavior():
    results = [run_benchmark_sample(sample.id) for sample in list_benchmark_samples()]

    assert len(results) >= 31
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

    assert result.sample_count >= 31
    assert result.pass_rate == 1.0
    assert result.verdict_match_rate == 1.0
    assert result.guardrail_pass_rate == 1.0
    assert result.failing_sample_ids == ()
    assert result.calibration_version == CALIBRATION_VERSION
    assert result.gate is not None
    assert result.gate.overall_pass == result.pass_rate
    assert result.gate.guardrail_pass == result.guardrail_pass_rate
    assert {summary.category for summary in result.category_summaries} >= {
        "False-positive guard",
        "Positive control",
    }


def test_calibration_gate_enforced_in_ci_mode():
    result = run_calibration_suite(
        min_overall_pass=0.9,
        min_guardrail_pass=0.95,
        strict=True,
    )

    assert result.gate is not None
    assert result.gate.passed
    assert not result.gate.failures


def test_calibration_gate_exposes_close_to_threshold_warning(tmp_path):
    sample_result = run_calibration_suite(persist_snapshot=False)
    warn_gate = evaluate_calibration_gate(sample_result, overall_threshold=0.97, guardrail_threshold=0.97)
    assert warn_gate.warnings
    assert warn_gate.passed
    assert not warn_gate.failures


def test_calibration_snapshot_is_persisted_for_local_reproducibility(tmp_path):
    snapshot_path = Path(tmp_path) / ".gauntlet" / "reports" / "latest_calibration.json"
    result = run_calibration_suite(snapshot_path=snapshot_path, persist_snapshot=True)

    assert snapshot_path.exists()
    assert result.snapshot_path == str(snapshot_path)
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert data["calibration_version"] == result.calibration_version
    assert data["sample_count"] == result.sample_count


def test_calibration_suite_strict_mode_with_impossible_threshold_fails():
    with pytest.raises(AssertionError, match="Calibration gate failed"):
        run_calibration_suite(min_overall_pass=1.01, min_guardrail_pass=0.99, strict=True, persist_snapshot=False)


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
