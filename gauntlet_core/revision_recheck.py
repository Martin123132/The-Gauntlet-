from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Literal

from .analysis import analyze_paper_text
from .models import AnalysisReport, utc_now_iso
from .repair_workshop import RepairStep


RevisionStatus = Literal["improved", "still-weak", "introduces-new-issue"]
REVISION_STATUSES: tuple[RevisionStatus, ...] = ("improved", "still-weak", "introduces-new-issue")


@dataclass(frozen=True)
class RevisionRecheckResult:
    id: str
    step_id: str
    status: RevisionStatus
    checked_at: str
    original_text: str
    revised_text: str
    original_verdict: str
    revised_verdict: str
    original_claim_status: str
    revised_claim_status: str
    original_gap_count: int
    revised_gap_count: int
    original_finding_count: int
    revised_finding_count: int
    remaining_gaps: tuple[str, ...]
    new_findings: tuple[str, ...]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def recheck_repair_revision(report: AnalysisReport, step: RepairStep, revised_text: str) -> RevisionRecheckResult:
    clean_revision = " ".join((revised_text or "").split())
    original_text = source_or_step_text(step)
    original_report = analyze_paper_text(original_text, source_name=f"original-{step.id}.txt")
    revised_report = analyze_paper_text(clean_revision, source_name=f"revision-{step.id}.txt")
    original_gaps = claim_gaps(original_report)
    revised_gaps = claim_gaps(revised_report)
    original_findings = finding_types(original_report)
    revised_findings = finding_types(revised_report)
    new_findings = tuple(sorted(set(revised_findings) - set(original_findings)))
    status = classify_revision(step, clean_revision, original_report, revised_report, original_gaps, revised_gaps, new_findings)
    return RevisionRecheckResult(
        id=revision_recheck_id(step.id, clean_revision),
        step_id=step.id,
        status=status,
        checked_at=utc_now_iso(),
        original_text=original_text,
        revised_text=clean_revision,
        original_verdict=original_report.verdict,
        revised_verdict=revised_report.verdict,
        original_claim_status=dominant_claim_status(original_report),
        revised_claim_status=dominant_claim_status(revised_report),
        original_gap_count=len(original_gaps),
        revised_gap_count=len(revised_gaps),
        original_finding_count=len(original_findings),
        revised_finding_count=len(revised_findings),
        remaining_gaps=tuple(sorted(revised_gaps)),
        new_findings=new_findings,
        summary=revision_summary(status, step, revised_report, revised_gaps, new_findings),
    )


def revision_recheck_log_to_markdown(report: AnalysisReport, results: dict[str, Any] | None) -> str:
    normalized = normalize_revision_rechecks(results or {})
    lines = [
        f"# Revision Re-Check Log: {report.source_name}",
        "",
        f"- Verdict: **{report.verdict}**",
        f"- Revision checks: **{len(normalized)}**",
        "",
    ]
    if not normalized:
        lines.extend(["No revision re-checks have been saved.", ""])
        return "\n".join(lines)
    for result in sorted(normalized.values(), key=lambda item: item.get("checked_at", ""), reverse=True):
        lines.extend(
            [
                f"## {result.get('id', 'Revision')} - {revision_status_label(result.get('status', 'still-weak'))}",
                "",
                f"- Step: {result.get('step_id', '')}",
                f"- Checked: {result.get('checked_at', '')}",
                f"- Original verdict: {result.get('original_verdict', '')}",
                f"- Revised verdict: {result.get('revised_verdict', '')}",
                f"- Original claim status: {result.get('original_claim_status', '')}",
                f"- Revised claim status: {result.get('revised_claim_status', '')}",
                f"- Gap count: {result.get('original_gap_count', 0)} -> {result.get('revised_gap_count', 0)}",
                f"- Finding count: {result.get('original_finding_count', 0)} -> {result.get('revised_finding_count', 0)}",
                f"- Remaining gaps: {', '.join(result.get('remaining_gaps', ())) or 'none'}",
                f"- New findings: {', '.join(result.get('new_findings', ())) or 'none'}",
                f"- Summary: {result.get('summary', '')}",
                "",
                "### Original Snippet",
                "",
                result.get("original_text", ""),
                "",
                "### Revised Snippet",
                "",
                result.get("revised_text", ""),
                "",
            ]
        )
    lines.extend(
        [
            "_Revision re-check logs contain only pasted revision snippets and deterministic audit results. They do not include the full uploaded paper file._",
            "",
        ]
    )
    return "\n".join(lines)


def normalize_revision_rechecks(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for step_id, value in raw.items():
        if not isinstance(step_id, str) or not isinstance(value, dict):
            continue
        status = normalize_revision_status(value.get("status"))
        normalized[step_id] = {
            "id": str(value.get("id", step_id)),
            "step_id": str(value.get("step_id", step_id)),
            "status": status,
            "checked_at": str(value.get("checked_at", "")),
            "original_text": str(value.get("original_text", "")),
            "revised_text": str(value.get("revised_text", "")),
            "original_verdict": str(value.get("original_verdict", "")),
            "revised_verdict": str(value.get("revised_verdict", "")),
            "original_claim_status": str(value.get("original_claim_status", "")),
            "revised_claim_status": str(value.get("revised_claim_status", "")),
            "original_gap_count": int(value.get("original_gap_count", 0)),
            "revised_gap_count": int(value.get("revised_gap_count", 0)),
            "original_finding_count": int(value.get("original_finding_count", 0)),
            "revised_finding_count": int(value.get("revised_finding_count", 0)),
            "remaining_gaps": tuple(value.get("remaining_gaps", ())),
            "new_findings": tuple(value.get("new_findings", ())),
            "summary": str(value.get("summary", "")),
        }
    return normalized


def revision_recheck_counts(results: dict[str, Any]) -> dict[str, int]:
    normalized = normalize_revision_rechecks(results)
    if not normalized:
        return {}
    counts = {status: 0 for status in REVISION_STATUSES}
    for result in normalized.values():
        status = normalize_revision_status(result.get("status"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def normalize_revision_status(status: object) -> RevisionStatus:
    if isinstance(status, str) and status in REVISION_STATUSES:
        return status  # type: ignore[return-value]
    return "still-weak"


def revision_status_label(status: str) -> str:
    labels = {
        "improved": "Improved",
        "still-weak": "Still Weak",
        "introduces-new-issue": "Introduces New Issue",
    }
    return labels.get(status, status.replace("-", " ").title())


def source_or_step_text(step: RepairStep) -> str:
    if step.source_span and step.source_span.text.strip():
        return step.source_span.text.strip()
    return step.body.strip()


def revision_recheck_id(step_id: str, revised_text: str) -> str:
    digest = hashlib.sha256(f"{step_id}|{revised_text}".encode("utf-8")).hexdigest()[:10].upper()
    return f"V{digest}"


def claim_gaps(report: AnalysisReport) -> tuple[str, ...]:
    return tuple(sorted({gap for claim in report.claims for gap in claim.gaps}))


def finding_types(report: AnalysisReport) -> tuple[str, ...]:
    return tuple(sorted({finding.type for finding in report.findings}))


def dominant_claim_status(report: AnalysisReport) -> str:
    if not report.claims:
        return "none"
    if any(claim.status == "resolved" for claim in report.claims):
        return "resolved"
    if any(claim.status == "partial" for claim in report.claims):
        return "partial"
    return "failed"


def classify_revision(
    step: RepairStep,
    revised_text: str,
    original_report: AnalysisReport,
    revised_report: AnalysisReport,
    original_gaps: tuple[str, ...],
    revised_gaps: tuple[str, ...],
    new_findings: tuple[str, ...],
) -> RevisionStatus:
    if len(revised_text) < 24 or not revised_report.claims:
        return "still-weak"
    if revised_report.verdict == "CREATES_NEW_PARADOXES" or any(finding.severity == "high" for finding in revised_report.findings):
        return "introduces-new-issue"
    if category_passes(step, revised_report, revised_gaps) and len(revised_gaps) <= len(original_gaps):
        return "improved"
    if new_findings and revised_report.verdict == "FAILS":
        return "introduces-new-issue"
    if revised_report.verdict in {"RESOLVES", "PARTIAL"} and len(revised_gaps) < len(original_gaps):
        return "improved"
    if dominant_claim_status(revised_report) != "failed" and dominant_claim_status(original_report) == "failed":
        return "improved"
    return "still-weak"


def category_passes(step: RepairStep, revised_report: AnalysisReport, revised_gaps: tuple[str, ...]) -> bool:
    category = step.category.lower()
    if "mechanism" in category:
        return any(claim.mechanism == "provided" for claim in revised_report.claims)
    if "evidence" in category:
        return revised_report.evidence.evidence_links != [] or revised_report.evidence.score >= 0.35
    if "specific" in category:
        return "details not specific" not in revised_gaps
    if "scope" in category:
        return "problem scope unclear" not in revised_gaps
    if "claim" in category:
        return bool(revised_report.claims)
    return revised_report.verdict in {"RESOLVES", "PARTIAL"} and not revised_gaps


def revision_summary(
    status: RevisionStatus,
    step: RepairStep,
    revised_report: AnalysisReport,
    revised_gaps: tuple[str, ...],
    new_findings: tuple[str, ...],
) -> str:
    if status == "improved":
        return f"The revision improves {step.title} under the deterministic checks."
    if status == "introduces-new-issue":
        issues = ", ".join(new_findings) or revised_report.verdict
        return f"The revision may introduce a new issue: {issues}."
    gaps = ", ".join(revised_gaps) or "claim/evidence support remains thin"
    return f"The revision still needs work: {gaps}."
