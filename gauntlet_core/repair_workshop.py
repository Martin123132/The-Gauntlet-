from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Literal

from .action_plan import ReviewerAction, build_reviewer_action_plan
from .models import AnalysisReport, SourceSpan, source_reference


RepairStatus = Literal["todo", "in-progress", "fixed", "wont-fix", "false-positive"]
REPAIR_STATUSES: tuple[RepairStatus, ...] = ("todo", "in-progress", "fixed", "wont-fix", "false-positive")
DEFAULT_REPAIR_STATUS: RepairStatus = "todo"


@dataclass(frozen=True)
class RepairStep:
    id: str
    priority: str
    category: str
    title: str
    target: str
    body: str
    explanation: str
    suggested_fix: str
    source_span: SourceSpan | None = None
    status: RepairStatus = DEFAULT_REPAIR_STATUS
    reviewer_note: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"source": source_reference(self.source_span)}


def build_repair_steps(report: AnalysisReport, progress: dict[str, Any] | None = None) -> list[RepairStep]:
    progress = progress or {}
    steps = [repair_step_from_action(action, progress.get(stable_repair_step_id(action), {})) for action in build_reviewer_action_plan(report, limit=24)]
    return sorted(steps, key=repair_step_sort_key)


def repair_workshop_to_markdown(report: AnalysisReport, steps: list[RepairStep] | None = None) -> str:
    repair_steps = steps if steps is not None else build_repair_steps(report)
    counts = repair_status_counts(repair_steps)
    lines = [
        f"# Repair Workshop: {report.source_name}",
        "",
        f"- Verdict: **{report.verdict}**",
        f"- Confidence: **{report.confidence:.0%}**",
        f"- Repair steps: **{len(repair_steps)}**",
        f"- Progress: {format_progress_counts(counts)}",
        "",
    ]
    if not repair_steps:
        lines.extend(["No repair steps were generated.", ""])
        return "\n".join(lines)

    for step in repair_steps:
        lines.extend(
            [
                f"## {step.id} - {step.title}",
                "",
                f"- Status: {repair_status_label(step.status)}",
                f"- Priority: {step.priority.upper()}",
                f"- Category: {step.category}",
                f"- Target: {step.target}",
                f"- Source: {source_reference(step.source_span)}",
                f"- Why it matters: {step.explanation}",
                f"- Suggested fix: {step.suggested_fix}",
            ]
        )
        if step.reviewer_note.strip():
            lines.append(f"- Reviewer note: {step.reviewer_note.strip()}")
        if step.updated_at:
            lines.append(f"- Updated: {step.updated_at}")
        lines.extend(["", step.body, ""])
        if step.source_span:
            lines.extend([f"> Source text: {step.source_span.text}", ""])

    lines.extend(
        [
            "_Repair Workshop exports contain source references, snippets, statuses, and reviewer notes only. They do not include the full uploaded paper file._",
            "",
        ]
    )
    return "\n".join(lines)


def repair_step_from_action(action: ReviewerAction, progress: dict[str, Any] | None = None) -> RepairStep:
    progress = progress if isinstance(progress, dict) else {}
    status = normalize_repair_status(progress.get("status"))
    return RepairStep(
        id=stable_repair_step_id(action),
        priority=action.priority,
        category=action.category,
        title=action.title,
        target=action.target,
        body=action.detail,
        explanation=action.detail,
        suggested_fix=action.suggested_fix,
        source_span=action.source_span,
        status=status,
        reviewer_note=str(progress.get("reviewer_note", "")),
        updated_at=str(progress.get("updated_at", "")),
    )


def stable_repair_step_id(action: ReviewerAction) -> str:
    anchor_id = action.source_span.anchor_id if action.source_span else ""
    raw = "|".join(
        [
            action.priority,
            action.category,
            action.title,
            action.target,
            anchor_id,
            action.detail,
            action.suggested_fix,
        ]
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10].upper()
    return f"R{digest}"


def normalize_repair_status(status: object) -> RepairStatus:
    if isinstance(status, str) and status in REPAIR_STATUSES:
        return status  # type: ignore[return-value]
    return DEFAULT_REPAIR_STATUS


def repair_status_label(status: str) -> str:
    labels = {
        "todo": "To Do",
        "in-progress": "In Progress",
        "fixed": "Fixed",
        "wont-fix": "Won't Fix",
        "false-positive": "False Positive",
    }
    return labels.get(status, status.replace("-", " ").title())


def repair_status_counts(steps: list[RepairStep]) -> dict[str, int]:
    counts = {status: 0 for status in REPAIR_STATUSES}
    for step in steps:
        counts[step.status] = counts.get(step.status, 0) + 1
    return counts


def format_progress_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{repair_status_label(status)} {counts.get(status, 0)}" for status in REPAIR_STATUSES)


def repair_step_sort_key(step: RepairStep) -> tuple[int, int, str, str]:
    status_order = {"todo": 0, "in-progress": 1, "false-positive": 2, "wont-fix": 3, "fixed": 4}
    priority_order = {"high": 0, "medium": 1, "low": 2}
    return (status_order.get(step.status, 5), priority_order.get(step.priority, 3), step.category, step.id)
