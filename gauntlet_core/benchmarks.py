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


@dataclass(frozen=True)
class CalibrationCategorySummary:
    category: str
    sample_count: int
    passed_count: int
    pass_rate: float
    verdict_match_rate: float
    guardrail_pass_rate: float
    failing_sample_ids: tuple[str, ...]


@dataclass(frozen=True)
class CalibrationSuiteResult:
    results: tuple[BenchmarkComparison, ...]
    sample_count: int
    passed_count: int
    pass_rate: float
    verdict_match_count: int
    verdict_match_rate: float
    guardrail_check_count: int
    guardrail_failure_count: int
    guardrail_pass_rate: float
    missed_finding_count: int
    extra_finding_count: int
    missed_claim_gap_count: int
    extra_claim_gap_count: int
    failing_sample_ids: tuple[str, ...]
    category_summaries: tuple[CalibrationCategorySummary, ...]

    def to_dict(self) -> dict:
        return {
            "sample_count": self.sample_count,
            "passed_count": self.passed_count,
            "pass_rate": self.pass_rate,
            "verdict_match_count": self.verdict_match_count,
            "verdict_match_rate": self.verdict_match_rate,
            "guardrail_check_count": self.guardrail_check_count,
            "guardrail_failure_count": self.guardrail_failure_count,
            "guardrail_pass_rate": self.guardrail_pass_rate,
            "missed_finding_count": self.missed_finding_count,
            "extra_finding_count": self.extra_finding_count,
            "missed_claim_gap_count": self.missed_claim_gap_count,
            "extra_claim_gap_count": self.extra_claim_gap_count,
            "failing_sample_ids": self.failing_sample_ids,
            "category_summaries": [asdict(summary) for summary in self.category_summaries],
            "samples": [calibration_sample_summary(result) for result in self.results],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_markdown(self) -> str:
        failing_cases = "\n".join(f"- `{sample_id}`" for sample_id in self.failing_sample_ids) or "- none"
        category_rows = "\n".join(
            (
                f"| {summary.category} | {summary.passed_count}/{summary.sample_count} | "
                f"{summary.pass_rate:.0%} | {summary.verdict_match_rate:.0%} | "
                f"{summary.guardrail_pass_rate:.0%} | {', '.join(summary.failing_sample_ids) or 'none'} |"
            )
            for summary in self.category_summaries
        )
        sample_rows = "\n".join(
            (
                f"| `{result.sample.id}` | {result.sample.category} | "
                f"{'pass' if result.passed else 'review'} | {result.sample.expected_verdict} | "
                f"{result.report.verdict} | {', '.join(result.missed_findings) or 'none'} | "
                f"{', '.join(result.extra_findings) or 'none'} | "
                f"{', '.join(result.unexpected_absent_findings + result.unexpected_absent_claim_gaps) or 'none'} |"
            )
            for result in self.results
        )
        return "\n".join(
            [
                "# The Gauntlet Calibration Suite",
                "",
                "Synthetic theory/paradox-paper cases for checking deterministic rule behavior. These samples are calibration fixtures, not proof of real-world accuracy.",
                "",
                "## Overall Metrics",
                "",
                f"- Samples: {self.sample_count}",
                f"- Overall pass rate: {self.pass_rate:.0%}",
                f"- Verdict-match rate: {self.verdict_match_rate:.0%}",
                f"- False-positive guardrail pass rate: {self.guardrail_pass_rate:.0%}",
                f"- Missed findings: {self.missed_finding_count}",
                f"- Extra findings: {self.extra_finding_count}",
                f"- Missed claim gaps: {self.missed_claim_gap_count}",
                f"- Extra claim gaps: {self.extra_claim_gap_count}",
                "",
                "## Category Calibration",
                "",
                "| Category | Passed | Pass Rate | Verdict Match | Guardrail Pass | Failing Cases |",
                "| --- | ---: | ---: | ---: | ---: | --- |",
                category_rows,
                "",
                "## Failing Cases",
                "",
                failing_cases,
                "",
                "## Sample Detail",
                "",
                "| Sample | Category | Result | Expected Verdict | Actual Verdict | Missed Findings | Extra Findings | Guardrail Failures |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
                sample_rows,
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
    BenchmarkSample(
        id="literature-review-background",
        title="Literature Review Background",
        category="False-positive guard",
        expected_verdict="FAILS",
        expected_findings=(),
        expected_claim_gaps=(),
        expected_absent_findings=("Evidence Gap", "Unsupported Resolution Claim", "Missing Mechanism Barrier", "Theory-As-Fact Language"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
        why_it_matters="Prevents literature-review context from being mistaken for this paper's own claimed resolution.",
        paper_text="""
        Literature Review
        Prior work by Smith et al. (2021) argues that the boundary paradox can be resolved by a sampling correction.
        Jones (2023) proposes a different interpretation for the same anomaly.
        This review summarizes those positions without adopting either resolution as the result of this paper.
        """,
    ),
    BenchmarkSample(
        id="definitions-only",
        title="Definitions Only",
        category="False-positive guard",
        expected_verdict="FAILS",
        expected_findings=(),
        expected_claim_gaps=(),
        expected_absent_findings=("Evidence Gap", "Unsupported Resolution Claim", "Theory-As-Fact Language"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
        why_it_matters="Keeps vocabulary and setup material from becoming audit findings when the document has not made an argument yet.",
        paper_text="""
        Definitions
        A paradox is a tension between assumptions, an anomaly is a measured departure, and a mechanism is a causal account.
        The term calibration boundary means the range where a method is valid.
        No resolution claim is offered in this glossary.
        """,
    ),
    BenchmarkSample(
        id="future-work-speculation",
        title="Future Work Speculation",
        category="False-positive guard",
        expected_verdict="PARTIAL",
        expected_findings=(),
        expected_claim_gaps=("details not specific",),
        expected_absent_findings=("Unsupported Resolution Claim", "Theory-As-Fact Language"),
        expected_absent_claim_gaps=("mechanism missing",),
        why_it_matters="Lets future-work language remain reviewable without treating it as a proven solution.",
        paper_text="""
        Future Work
        A later experiment may explain the anomaly if a boundary condition changes the sampling process.
        The proposal is speculative and will require a direct test before it can resolve the paradox.
        """,
    ),
    BenchmarkSample(
        id="null-result-boundary",
        title="Null Result Boundary",
        category="False-positive guard",
        expected_verdict="FAILS",
        expected_findings=(),
        expected_claim_gaps=(),
        expected_absent_findings=("Unsupported Resolution Claim", "Missing Mechanism Barrier", "Scope Conflict"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
        why_it_matters="Checks that a null result or boundary note is not upgraded into a failed resolution claim.",
        paper_text="""
        Results
        The null result rules out one broad parameter range but leaves the anomaly unresolved.
        The paper does not resolve the paradox or offer a mechanism for the remaining cases.
        """,
    ),
    BenchmarkSample(
        id="theorem-proof-resolution",
        title="Theorem Proof Resolution",
        category="Positive control",
        expected_verdict="RESOLVES",
        expected_findings=(),
        expected_claim_gaps=(),
        expected_absent_findings=("Evidence Gap", "Unsupported Resolution Claim", "Theory-As-Fact Language"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
        why_it_matters="Shows that theorem/proof wording can pass when it states a mechanism, proof structure, and scoped support.",
        paper_text="""
        Theorem 3
        The theorem specifically resolves the parity paradox through a constructive mechanism that maps admissible states within the theorem domain to one invariant class.
        Proof
        Equation p = q + 2 defines the invariant, lemma 2 proves the boundary step, and the derivation specifically predicts the measured parity shift by 8 percent.
        Corollary
        Smith et al. (2024) report the same invariant in 16 simulated cases with error = 0.01.
        """,
    ),
    BenchmarkSample(
        id="method-only-section",
        title="Method-Only Section",
        category="False-positive guard",
        expected_verdict="FAILS",
        expected_findings=(),
        expected_claim_gaps=(),
        expected_absent_findings=("Evidence Gap", "Unsupported Resolution Claim", "Missing Mechanism Barrier"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
        why_it_matters="Keeps procedural method notes from becoming claims when they do not say what problem the method resolves.",
        paper_text="""
        Methods
        We normalize the samples, compute RMSE = 0.05, and compare three calibration windows.
        The section reports procedure only and does not interpret or resolve the anomaly.
        """,
    ),
    BenchmarkSample(
        id="limitation-section-only",
        title="Limitation Section Only",
        category="False-positive guard",
        expected_verdict="FAILS",
        expected_findings=(),
        expected_claim_gaps=(),
        expected_absent_findings=("Scope Conflict", "Unsupported Resolution Claim", "Missing Mechanism Barrier"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
        why_it_matters="Stops limitation-only text from being scored as if it made and then contradicted a central claim.",
        paper_text="""
        Limitations
        The analysis is not a completed resolution and does not apply outside the calibration window.
        Boundary cases remain open, and no mechanism is claimed for those cases.
        """,
    ),
    BenchmarkSample(
        id="competing-hypotheses",
        title="Competing Hypotheses",
        category="False-positive guard",
        expected_verdict="PARTIAL",
        expected_findings=("Evidence Gap",),
        expected_claim_gaps=("details not specific", "evidence not linked"),
        expected_absent_findings=("Unsupported Resolution Claim", "Scope Conflict", "Temporal Conflict"),
        expected_absent_claim_gaps=("mechanism missing",),
        why_it_matters="Checks that several candidate explanations are reviewed for evidence instead of being collapsed into an internal contradiction.",
        paper_text="""
        Hypothesis A may explain the anomaly through a local feedback process that changes the boundary term.
        Hypothesis B may explain the anomaly through a measurement drift process that changes the same term.
        The paper compares these options but does not decide between them.
        """,
    ),
    BenchmarkSample(
        id="citation-heavy-background",
        title="Citation-Heavy Background",
        category="False-positive guard",
        expected_verdict="FAILS",
        expected_findings=(),
        expected_claim_gaps=(),
        expected_absent_findings=("Evidence Gap", "Unsupported Resolution Claim", "Missing Mechanism Barrier"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
        why_it_matters="Protects citation-heavy background paragraphs from producing apparent paper-level claims.",
        paper_text="""
        Background
        Smith et al. (2021), Jones (2022), and Rivera (2024) each suggest that the paradox can be resolved by different boundary assumptions.
        The present section reviews those citations and does not state this paper solves the anomaly.
        """,
    ),
    BenchmarkSample(
        id="empirical-mechanism-positive",
        title="Empirical Mechanism Positive",
        category="Positive control",
        expected_verdict="RESOLVES",
        expected_findings=(),
        expected_claim_gaps=(),
        expected_absent_findings=("Evidence Gap", "Unsupported Resolution Claim", "Scope Conflict"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
        why_it_matters="Confirms that a local empirical mechanism claim can still receive a resolving verdict after the false-positive guardrails tighten.",
        paper_text="""
        Abstract
        The paper resolves the anomaly in the calibrated sample through a measured transfer mechanism that specifically predicts the observed 11 percent shift.
        Results
        Specifically, across 24 trials, the transfer term is measured before the anomaly appears, with equation t = a + b and RMSE = 0.03.
        Smith et al. (2025) report an independent replication, and Jones (2026) validates the same transfer pattern with error = 0.02.
        """,
    ),
    BenchmarkSample(
        id="clean-limitation-aware-resolution",
        title="Clean Limitation-Aware Resolution",
        category="Positive control",
        expected_verdict="RESOLVES",
        expected_findings=(),
        expected_claim_gaps=(),
        expected_absent_findings=("Scope Conflict", "Temporal Conflict", "Unsupported Resolution Claim"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
        why_it_matters="Shows that honest boundaries should not stop a well-supported scoped resolution from passing.",
        paper_text="""
        Abstract
        The framework specifically resolves the paradox within low-energy trials by a bounded exchange mechanism that predicts the observed 9 percent residual.
        Evidence
        The paper compares 30 measured trials, reports RMSE = 0.04, includes equation r = kx, and cites Rivera et al. (2024) replication data.
        Limitations
        The claim is limited to low-energy trials and does not extend to untested high-energy cases.
        """,
    ),
    BenchmarkSample(
        id="citation-as-claim-guard",
        title="Citation As Claim Guard",
        category="False-positive guard",
        expected_verdict="FAILS",
        expected_findings=(),
        expected_claim_gaps=(),
        expected_absent_findings=("Unsupported Resolution Claim", "Evidence Gap", "Theory-As-Fact Language"),
        expected_absent_claim_gaps=("mechanism missing", "evidence not linked"),
        why_it_matters="Checks that attributed claims by other authors do not become this paper's own unresolved claim.",
        paper_text="""
        Background
        Several authors argue that the paradox is resolved once the hidden boundary term is introduced (Smith 2020; Lee 2021).
        This note catalogues the argument without claiming that the resolution is correct.
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


def run_calibration_suite() -> CalibrationSuiteResult:
    return summarize_calibration_results(run_all_benchmarks())


def summarize_calibration_results(results: tuple[BenchmarkComparison, ...]) -> CalibrationSuiteResult:
    sample_count = len(results)
    passed_count = sum(1 for result in results if result.passed)
    verdict_match_count = sum(1 for result in results if result.verdict_match)
    total_guardrail_checks = sum(guardrail_check_count(result) for result in results)
    total_guardrail_failures = sum(guardrail_failure_count(result) for result in results)
    categories = tuple(sorted({result.sample.category for result in results}))
    category_summaries = tuple(summarize_calibration_category(category, results) for category in categories)
    return CalibrationSuiteResult(
        results=results,
        sample_count=sample_count,
        passed_count=passed_count,
        pass_rate=ratio(passed_count, sample_count),
        verdict_match_count=verdict_match_count,
        verdict_match_rate=ratio(verdict_match_count, sample_count),
        guardrail_check_count=total_guardrail_checks,
        guardrail_failure_count=total_guardrail_failures,
        guardrail_pass_rate=ratio(total_guardrail_checks - total_guardrail_failures, total_guardrail_checks, empty=1.0),
        missed_finding_count=sum(len(result.missed_findings) for result in results),
        extra_finding_count=sum(len(result.extra_findings) for result in results),
        missed_claim_gap_count=sum(len(result.missed_claim_gaps) for result in results),
        extra_claim_gap_count=sum(len(result.extra_claim_gaps) for result in results),
        failing_sample_ids=tuple(result.sample.id for result in results if not result.passed),
        category_summaries=category_summaries,
    )


def summarize_calibration_category(category: str, results: tuple[BenchmarkComparison, ...]) -> CalibrationCategorySummary:
    category_results = tuple(result for result in results if result.sample.category == category)
    sample_count = len(category_results)
    passed_count = sum(1 for result in category_results if result.passed)
    verdict_match_count = sum(1 for result in category_results if result.verdict_match)
    checks = sum(guardrail_check_count(result) for result in category_results)
    failures = sum(guardrail_failure_count(result) for result in category_results)
    return CalibrationCategorySummary(
        category=category,
        sample_count=sample_count,
        passed_count=passed_count,
        pass_rate=ratio(passed_count, sample_count),
        verdict_match_rate=ratio(verdict_match_count, sample_count),
        guardrail_pass_rate=ratio(checks - failures, checks, empty=1.0),
        failing_sample_ids=tuple(result.sample.id for result in category_results if not result.passed),
    )


def guardrail_check_count(result: BenchmarkComparison) -> int:
    return (
        len(result.absent_findings_kept_out)
        + len(result.unexpected_absent_findings)
        + len(result.absent_claim_gaps_kept_out)
        + len(result.unexpected_absent_claim_gaps)
    )


def guardrail_failure_count(result: BenchmarkComparison) -> int:
    return len(result.unexpected_absent_findings) + len(result.unexpected_absent_claim_gaps)


def ratio(numerator: int, denominator: int, empty: float = 0.0) -> float:
    if denominator == 0:
        return empty
    return round(numerator / denominator, 3)


def calibration_sample_summary(result: BenchmarkComparison) -> dict:
    return {
        "sample_id": result.sample.id,
        "title": result.sample.title,
        "category": result.sample.category,
        "expected_verdict": result.sample.expected_verdict,
        "actual_verdict": result.report.verdict,
        "passed": result.passed,
        "score": result.score,
        "matched_findings": result.matched_findings,
        "missed_findings": result.missed_findings,
        "extra_findings": result.extra_findings,
        "matched_claim_gaps": result.matched_claim_gaps,
        "missed_claim_gaps": result.missed_claim_gaps,
        "extra_claim_gaps": result.extra_claim_gaps,
        "unexpected_absent_findings": result.unexpected_absent_findings,
        "unexpected_absent_claim_gaps": result.unexpected_absent_claim_gaps,
    }


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
