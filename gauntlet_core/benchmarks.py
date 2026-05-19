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
    expected_absent_findings: tuple[str, ...] = ()
    expected_absent_claim_gaps: tuple[str, ...] = ()


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
    absent_findings_kept_out: tuple[str, ...]
    unexpected_absent_findings: tuple[str, ...]
    absent_claim_gaps_kept_out: tuple[str, ...]
    unexpected_absent_claim_gaps: tuple[str, ...]
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
                f"- Benchmark result: **{'EXPECTED MATCH' if self.passed else 'NEEDS REVIEW'}**",
                f"- Benchmark match: **{self.score:.0%}**",
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
                "## False-Positive Guardrails",
                "",
                f"- Findings kept out: {', '.join(self.absent_findings_kept_out) or 'none'}",
                f"- Unexpected guarded findings: {', '.join(self.unexpected_absent_findings) or 'none'}",
                f"- Claim gaps kept out: {', '.join(self.absent_claim_gaps_kept_out) or 'none'}",
                f"- Unexpected guarded claim gaps: {', '.join(self.unexpected_absent_claim_gaps) or 'none'}",
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
        expected_absent_findings=("Evidence Gap", "Unsupported Resolution Claim", "Scope Conflict", "Theory-As-Fact Language"),
        expected_absent_claim_gaps=("evidence not linked", "mechanism missing"),
        why_it_matters="Shows what a clean expected match looks like when claims include a mechanism, numbers, citations, and an evidence trail.",
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
        expected_absent_findings=("Evidence Gap", "Unsupported Resolution Claim", "Theory-As-Fact Language"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
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
    BenchmarkSample(
        id="tentative-hypothesis",
        title="Tentative Hypothesis",
        category="False-positive guard",
        expected_verdict="PARTIAL",
        expected_findings=("Evidence Gap",),
        expected_claim_gaps=("details not specific", "evidence not linked"),
        expected_absent_findings=("Unsupported Resolution Claim", "Theory-As-Fact Language"),
        expected_absent_claim_gaps=("mechanism missing",),
        why_it_matters="Checks that cautious hypothesis language can be reviewed without being mistaken for a finished resolution claim.",
        paper_text="""
        We hypothesize that the framework may explain the anomaly if a boundary condition changes the sampling process.
        This is a tentative proposal rather than a completed resolution, and it still requires a direct test.
        """,
    ),
    BenchmarkSample(
        id="scoped-limitation",
        title="Scoped Limitation",
        category="False-positive guard",
        expected_verdict="PARTIAL",
        expected_findings=("Evidence Gap",),
        expected_claim_gaps=("details not specific", "evidence not linked"),
        expected_absent_findings=("Scope Conflict", "Temporal Conflict", "Unsupported Resolution Claim"),
        expected_absent_claim_gaps=("mechanism missing",),
        why_it_matters="Protects limitation sections from being misread as contradictions when they define the boundary of the claim.",
        paper_text="""
        The framework explains the anomaly through a sampling process under low-energy boundary conditions.
        The claim is limited to the calibrated sample and does not apply outside that scope.
        """,
    ),
    BenchmarkSample(
        id="prior-work-comparison",
        title="Prior-Work Comparison",
        category="False-positive guard",
        expected_verdict="PARTIAL",
        expected_findings=("Evidence Gap",),
        expected_claim_gaps=("details not specific", "evidence not linked"),
        expected_absent_findings=("Potential Direct Negation", "Property Mismatch", "Scope Conflict", "Temporal Conflict"),
        expected_absent_claim_gaps=("mechanism missing",),
        why_it_matters="Checks that comparisons with older theories do not become internal contradiction findings against the current paper.",
        paper_text="""
        Prior work claimed the signal was always constant in every measurement.
        Unlike the conventional model, this framework explains the anomaly through a boundary process where the signal changes after calibration.
        """,
    ),
    BenchmarkSample(
        id="reference-like-text",
        title="Reference-Like Text",
        category="False-positive guard",
        expected_verdict="FAILS",
        expected_findings=(),
        expected_claim_gaps=(),
        expected_absent_findings=("Evidence Gap", "Unsupported Resolution Claim", "Theory-As-Fact Language"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
        why_it_matters="Prevents citation-heavy reference snippets from being promoted into claims or evidence-backed verdicts by accident.",
        paper_text="""
        References
        Smith et al. (2021), Journal of Tests, 14, 22-31; Jones (2023), Methods Review, 9, 100-118.
        Lee (2024), Experimental Notes, 2, 3-6; Patel (2020), Archive of Models, 7, 40-59.
        """,
    ),
    BenchmarkSample(
        id="equation-dump-without-claim-link",
        title="Equation Dump Without Claim Link",
        category="False-positive guard",
        expected_verdict="FAILS",
        expected_findings=(),
        expected_claim_gaps=(),
        expected_absent_findings=("Unsupported Resolution Claim", "Scope Conflict", "Theory-As-Fact Language"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
        why_it_matters="Keeps isolated equations and metrics from creating a successful verdict when no claim connects them to a problem.",
        paper_text="""
        Methods
        Equation x = y + 2. RMSE = 0.04. R2 = 0.91. The derivation has three algebraic steps.
        No interpretation, paradox, contradiction, or resolution claim is provided in this note.
        """,
    ),
    BenchmarkSample(
        id="caveated-universal-claim",
        title="Caveated Universal Claim",
        category="False-positive guard",
        expected_verdict="PARTIAL",
        expected_findings=(),
        expected_claim_gaps=("details not specific",),
        expected_absent_findings=("Scope Conflict", "Temporal Conflict"),
        expected_absent_claim_gaps=("mechanism missing",),
        why_it_matters="Checks that universal-sounding language is tolerated when the sentence itself clearly names its limited domain.",
        paper_text="""
        Within the calibrated sample, every signal remains conserved because the bounded model separates local and global cases.
        This statement is limited to the calibrated sample and does not apply outside the boundary condition.
        """,
    ),
    BenchmarkSample(
        id="assertive-model-authority",
        title="Assertive Model Authority",
        category="Assumption barrier",
        expected_verdict="PARTIAL",
        expected_findings=("Theory-As-Fact Language",),
        expected_claim_gaps=("details not specific",),
        why_it_matters="Makes sure the false-positive guardrails still catch assertive model-authority language when it replaces evidence.",
        paper_text="""
        The model proves that the paradox is impossible because the theory dictates that all violations are forbidden.
        The framework explains the anomaly through a formal mechanism, but it gives no measurement or test.
        """,
    ),
    BenchmarkSample(
        id="strong-with-limitations",
        title="Strong Claim With Limitations",
        category="Positive control",
        expected_verdict="RESOLVES",
        expected_findings=(),
        expected_claim_gaps=(),
        expected_absent_findings=("Scope Conflict", "Temporal Conflict", "Unsupported Resolution Claim"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
        why_it_matters="Checks that a strong evidence-backed claim can still pass when a separate limitation section honestly narrows external validity.",
        paper_text="""
        Abstract
        The framework resolves the anomaly through a bounded mechanism that specifically predicts the measured shift by 12 percent with RMSE = 0.02.
        Evidence
        The method compares the prediction against four datasets, includes equation z = ax + c, and reports RMSE = 0.02.
        Rivera et al. (2024) report measurements that support the same prediction in a preregistered sample.
        Limitations
        Outside this dataset the framework is not tested, so the conclusion is limited to the calibrated sample.
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
    expected_absent_findings = tuple(sorted(sample.expected_absent_findings))
    expected_absent_gaps = tuple(sorted(sample.expected_absent_claim_gaps))

    matched_findings = tuple(finding for finding in expected_findings if finding in actual_findings)
    missed_findings = tuple(finding for finding in expected_findings if finding not in actual_findings)
    extra_findings = tuple(finding for finding in actual_findings if finding not in expected_findings)
    matched_gaps = tuple(gap for gap in expected_gaps if gap in actual_gaps)
    missed_gaps = tuple(gap for gap in expected_gaps if gap not in actual_gaps)
    extra_gaps = tuple(gap for gap in actual_gaps if gap not in expected_gaps)
    absent_findings_kept_out = tuple(finding for finding in expected_absent_findings if finding not in actual_findings)
    unexpected_absent_findings = tuple(finding for finding in expected_absent_findings if finding in actual_findings)
    absent_gaps_kept_out = tuple(gap for gap in expected_absent_gaps if gap not in actual_gaps)
    unexpected_absent_gaps = tuple(gap for gap in expected_absent_gaps if gap in actual_gaps)
    verdict_match = report.verdict == sample.expected_verdict

    clean_case_has_extras = not expected_findings and bool(extra_findings)
    clean_gap_case_has_extras = not expected_gaps and bool(extra_gaps)
    passed = (
        verdict_match
        and not missed_findings
        and not missed_gaps
        and not clean_case_has_extras
        and not clean_gap_case_has_extras
        and not unexpected_absent_findings
        and not unexpected_absent_gaps
    )
    checks = [
        verdict_match,
        not missed_findings,
        not missed_gaps,
        not clean_case_has_extras,
        not clean_gap_case_has_extras,
        not unexpected_absent_findings,
        not unexpected_absent_gaps,
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
        absent_findings_kept_out=absent_findings_kept_out,
        unexpected_absent_findings=unexpected_absent_findings,
        absent_claim_gaps_kept_out=absent_gaps_kept_out,
        unexpected_absent_claim_gaps=unexpected_absent_gaps,
        passed=passed,
        score=score,
    )
