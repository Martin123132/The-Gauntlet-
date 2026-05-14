from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .analysis import analyze_paper_text
from .models import AnalysisReport, Verdict


@dataclass(frozen=True)
class BenchmarkSample:
    id: str
    title: str
    category: str
    paper_text: str
    expected_verdict: Verdict
    expected_findings: tuple[str, ...]
    expected_claim_gaps: tuple[str, ...]
    why_it_matters: str


@dataclass(frozen=True)
class BenchmarkComparison:
    sample: BenchmarkSample
    report: AnalysisReport
    verdict_match: bool
    matched_findings: tuple[str, ...]
    missed_findings: tuple[str, ...]
    extra_findings: tuple[str, ...]
    matched_claim_gaps: tuple[str, ...]
    missed_claim_gaps: tuple[str, ...]
    extra_claim_gaps: tuple[str, ...]
    passed: bool
    score: float

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_markdown(self) -> str:
        return "\n".join(
            [
                f"# The Gauntlet Benchmark: {self.sample.title}",
                "",
                f"- Sample ID: `{self.sample.id}`",
                f"- Category: {self.sample.category}",
                f"- Expected verdict: **{self.sample.expected_verdict}**",
                f"- Actual verdict: **{self.report.verdict}**",
                f"- Result: **{'PASS' if self.passed else 'REVIEW'}**",
                f"- Match score: **{self.score:.0%}**",
                "",
                "## Why This Matters",
                "",
                self.sample.why_it_matters,
                "",
                "## Finding Comparison",
                "",
                f"- Matched: {', '.join(self.matched_findings) or 'none'}",
                f"- Missed: {', '.join(self.missed_findings) or 'none'}",
                f"- Extra: {', '.join(self.extra_findings) or 'none'}",
                "",
                "## Claim Gap Comparison",
                "",
                f"- Matched: {', '.join(self.matched_claim_gaps) or 'none'}",
                f"- Missed: {', '.join(self.missed_claim_gaps) or 'none'}",
                f"- Extra: {', '.join(self.extra_claim_gaps) or 'none'}",
                "",
                "## Actual Report Summary",
                "",
                self.report.summary,
                "",
            ]
        )


BENCHMARK_SAMPLES: tuple[BenchmarkSample, ...] = (
    BenchmarkSample(
        id="strong-mechanism-evidence",
        title="Strong Mechanism + Evidence",
        category="Positive control",
        expected_verdict="RESOLVES",
        expected_findings=(),
        expected_claim_gaps=(),
        why_it_matters="Shows what a clean pass looks like when claims include a mechanism, numbers, citations, and an evidence trail.",
        paper_text="""
        Abstract
        The framework resolves the anomaly through a geometric mechanism that specifically predicts the measured curve by 14.2 percent.
        Evidence
        The paper explains the discrepancy using equation y = mx + b and specifically compares the result against three observational datasets.
        Smith et al. (2021) and Jones (2023) report measurements that support the same prediction with RMSE = 0.03.
        """,
    ),
    BenchmarkSample(
        id="weak-evidence",
        title="Weak Evidence",
        category="Evidence gap",
        expected_verdict="PARTIAL",
        expected_findings=("Evidence Gap",),
        expected_claim_gaps=("evidence not linked", "details not specific"),
        why_it_matters="Checks that a claim with a mechanism-like phrase still gets flagged when it does not connect to evidence.",
        paper_text="The framework addresses the issue using a process.",
    ),
    BenchmarkSample(
        id="no-clear-claims",
        title="No Clear Resolution Claims",
        category="Claim extraction",
        expected_verdict="FAILS",
        expected_findings=(),
        expected_claim_gaps=(),
        why_it_matters="Confirms the checker does not invent a verdict when a document describes a topic without making a resolution claim.",
        paper_text="This short note describes a topic, its history, and some vocabulary without making a resolution claim.",
    ),
    BenchmarkSample(
        id="unsupported-resolution",
        title="Unsupported Resolution Claim",
        category="Repair barrier",
        expected_verdict="FAILS",
        expected_findings=("Missing Mechanism Barrier", "Evidence Gap", "Unsupported Resolution Claim"),
        expected_claim_gaps=("mechanism missing", "evidence not linked", "details not specific"),
        why_it_matters="Catches papers that claim to solve a paradox but do not say how the solution works or what evidence supports it.",
        paper_text="The paper resolves the paradox and eliminates the contradiction.",
    ),
    BenchmarkSample(
        id="internal-contradiction",
        title="Internal Contradiction",
        category="Contradiction detection",
        expected_verdict="CREATES_NEW_PARADOXES",
        expected_findings=("Temporal Conflict",),
        expected_claim_gaps=("details not specific",),
        why_it_matters="Shows that a paper can include a mechanism and evidence markers while still failing because it creates a new conflict.",
        paper_text="""
        The framework resolves the contradiction because the model provides a mechanism and equation x = 1 with data from Smith et al. (2021).
        The framework states the signal is always constant in 1990.
        The framework states the signal changed in 2020 after the same measurement process.
        """,
    ),
    BenchmarkSample(
        id="scope-conflict",
        title="Scope Conflict",
        category="Scope control",
        expected_verdict="PARTIAL",
        expected_findings=("Scope Conflict", "Theory-As-Fact Language"),
        expected_claim_gaps=("details not specific",),
        why_it_matters="Tests whether broad universal language is flagged when the same text also admits boundary cases.",
        paper_text="""
        The framework resolves the paradox because the model says that every signal is always conserved.
        However, under boundary cases the signal can change when the sampling frame changes.
        """,
    ),
    BenchmarkSample(
        id="circular-support",
        title="Circular Support",
        category="Reasoning structure",
        expected_verdict="PARTIAL",
        expected_findings=("Potential Circular Reasoning", "Evidence Gap"),
        expected_claim_gaps=("evidence not linked", "details not specific"),
        why_it_matters="Checks that repeated because/therefore loops are visible instead of being mistaken for real support.",
        paper_text="""
        The framework resolves the paradox because the geometry stabilizes the contradiction.
        Therefore the geometry stabilizes the contradiction because the framework resolves the paradox.
        The paper explains the anomaly because the resolved state follows from the same resolved state.
        """,
    ),
    BenchmarkSample(
        id="theory-as-fact",
        title="Theory-As-Fact Language",
        category="Assumption barrier",
        expected_verdict="PARTIAL",
        expected_findings=("Theory-As-Fact Language",),
        expected_claim_gaps=("details not specific",),
        why_it_matters="Checks that model-authority language is surfaced so users can replace it with evidence-based wording.",
        paper_text="""
        The theory proves that the paradox is impossible because the model says the framework forbids it.
        The paper explains the anomaly through a formal mechanism, but it provides no observations.
        """,
    ),
)


def list_benchmark_samples() -> tuple[BenchmarkSample, ...]:
    return BENCHMARK_SAMPLES


def get_benchmark_sample(sample_id: str) -> BenchmarkSample:
    for sample in BENCHMARK_SAMPLES:
        if sample.id == sample_id:
            return sample
    raise KeyError(f"Unknown benchmark sample: {sample_id}")


def run_benchmark_sample(sample_id: str) -> BenchmarkComparison:
    sample = get_benchmark_sample(sample_id)
    report = analyze_paper_text(sample.paper_text, source_name=f"benchmark-{sample.id}.txt")
    return compare_report_to_sample(sample, report)


def run_all_benchmarks() -> tuple[BenchmarkComparison, ...]:
    return tuple(run_benchmark_sample(sample.id) for sample in BENCHMARK_SAMPLES)


def compare_report_to_sample(sample: BenchmarkSample, report: AnalysisReport) -> BenchmarkComparison:
    actual_findings = tuple(sorted({finding.type for finding in report.findings}))
    actual_gaps = tuple(sorted({gap for claim in report.claims for gap in claim.gaps}))
    expected_findings = tuple(sorted(sample.expected_findings))
    expected_gaps = tuple(sorted(sample.expected_claim_gaps))

    matched_findings = tuple(finding for finding in expected_findings if finding in actual_findings)
    missed_findings = tuple(finding for finding in expected_findings if finding not in actual_findings)
    extra_findings = tuple(finding for finding in actual_findings if finding not in expected_findings)
    matched_gaps = tuple(gap for gap in expected_gaps if gap in actual_gaps)
    missed_gaps = tuple(gap for gap in expected_gaps if gap not in actual_gaps)
    extra_gaps = tuple(gap for gap in actual_gaps if gap not in expected_gaps)
    verdict_match = report.verdict == sample.expected_verdict

    clean_case_has_extras = not expected_findings and bool(extra_findings)
    clean_gap_case_has_extras = not expected_gaps and bool(extra_gaps)
    passed = verdict_match and not missed_findings and not missed_gaps and not clean_case_has_extras and not clean_gap_case_has_extras
    checks = [
        verdict_match,
        not missed_findings,
        not missed_gaps,
        not clean_case_has_extras,
        not clean_gap_case_has_extras,
    ]
    score = sum(1 for check in checks if check) / len(checks)

    return BenchmarkComparison(
        sample=sample,
        report=report,
        verdict_match=verdict_match,
        matched_findings=matched_findings,
        missed_findings=missed_findings,
        extra_findings=extra_findings,
        matched_claim_gaps=matched_gaps,
        missed_claim_gaps=missed_gaps,
        extra_claim_gaps=extra_gaps,
        passed=passed,
        score=score,
    )
