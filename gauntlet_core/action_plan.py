from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import AnalysisReport, ClaimResult, Finding, SourceSpan, source_reference


ActionPriority = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class ReviewerAction:
    id: str
    priority: ActionPriority
    category: str
    title: str
    target: str
    detail: str
    suggested_fix: str
    source_span: SourceSpan | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "priority": self.priority,
            "category": self.category,
            "title": self.title,
            "target": self.target,
            "detail": self.detail,
            "suggested_fix": self.suggested_fix,
            "source": source_reference(self.source_span),
            "source_span": self.source_span,
        }


def build_reviewer_action_plan(report: AnalysisReport, limit: int = 12) -> list[ReviewerAction]:
    actions: list[ReviewerAction] = []

    for finding in report.findings:
        priority: ActionPriority = "high" if finding.severity == "high" else "medium" if finding.severity == "medium" else "low"
        target = finding.claim_id or finding.id or finding.type
        actions.append(
            ReviewerAction(
                id="",
                priority=priority,
                category=finding.type,
                title=f"Resolve {finding.type}",
                target=target,
                detail=finding.explanation,
                suggested_fix=finding.repair_suggestion,
                source_span=finding.source_span,
            )
        )

    for claim in report.claims:
        actions.extend(actions_for_claim(claim))

    if not report.claims:
        actions.append(
            ReviewerAction(
                id="",
                priority="high",
                category="Claim Structure",
                title="State a testable resolution claim",
                target="Document",
                detail="The checker did not find a clear claim that names what problem is being resolved.",
                suggested_fix="Add one explicit sentence that names the paradox or problem, the proposed resolution, and what would count as evidence against it.",
            )
        )

    if report.evidence.score < 0.35:
        actions.append(
            ReviewerAction(
                id="",
                priority="high" if report.evidence.score < 0.2 else "medium",
                category="Evidence Coverage",
                title="Strengthen the evidence base",
                target="Document",
                detail=f"The document-level evidence score is {report.evidence.score:.2f}/1.00.",
                suggested_fix="Add citations, observations, measurements, equations, derivations, methods, or falsifiable tests near the claims they support.",
            )
        )

    if report.verdict == "RESOLVES" and not actions:
        actions.append(
            ReviewerAction(
                id="",
                priority="low",
                category="Review Hygiene",
                title="Preserve source traceability",
                target="Document",
                detail="The rule audit did not identify a blocking repair item.",
                suggested_fix="Keep each claim tied to its evidence and mechanism when revising the paper.",
            )
        )

    return assign_action_ids(deduplicate_actions(actions))[:limit]


def actions_for_claim(claim: ClaimResult) -> list[ReviewerAction]:
    actions: list[ReviewerAction] = []
    target = claim.id or "Claim"
    for gap in claim.gaps:
        priority, category, title, detail, fix = action_for_gap(gap, claim)
        actions.append(
            ReviewerAction(
                id="",
                priority=priority,
                category=category,
                title=title,
                target=target,
                detail=detail,
                suggested_fix=fix,
                source_span=claim.source_span,
            )
        )

    if claim.status == "failed" and not claim.gaps:
        actions.append(
            ReviewerAction(
                id="",
                priority="medium",
                category="Claim Support",
                title=f"Repair support for {target}",
                target=target,
                detail="The claim failed the local rubric but did not expose a single dominant gap.",
                suggested_fix=claim.repair_suggestion or "Restate the claim with mechanism, evidence, and scope boundaries.",
                source_span=claim.source_span,
            )
        )
    return actions


def action_for_gap(gap: str, claim: ClaimResult) -> tuple[ActionPriority, str, str, str, str]:
    target = claim.id or "this claim"
    if gap == "mechanism missing":
        return (
            "high" if claim.status == "failed" else "medium",
            "Mechanism",
            f"Add a mechanism for {target}",
            "The claim names a resolution but does not explain the process that makes the resolution happen.",
            "Name the mechanism, proof step, equation, causal pathway, or operational process that carries the claim.",
        )
    if gap == "evidence not linked":
        return (
            "high" if claim.status == "failed" else "medium",
            "Evidence",
            f"Link evidence to {target}",
            "The claim is not tied to nearby evidence markers such as data, citations, measurements, derivations, or methods.",
            "Place a citation, measurement, derivation, test, or falsifiable prediction next to the claim it supports.",
        )
    if gap == "details not specific":
        return (
            "medium",
            "Specificity",
            f"Make {target} more specific",
            "The claim is too broad for the rule audit to see boundaries, examples, or conditions.",
            "Add concrete conditions, variables, examples, limits, or boundary cases.",
        )
    if gap == "problem scope unclear":
        return (
            "medium",
            "Scope",
            f"Clarify the scope of {target}",
            "The claim does not clearly name the paradox, contradiction, or problem it is resolving.",
            "State the exact problem and define what is inside or outside the claim's scope.",
        )
    return (
        "medium",
        "Claim Repair",
        f"Repair {target}",
        f"The claim has this gap: {gap}.",
        claim.repair_suggestion or "Tie the claim to mechanism, evidence, and scope.",
    )


def action_plan_to_markdown(report: AnalysisReport) -> str:
    actions = build_reviewer_action_plan(report)
    lines = [
        "# Reviewer Action Plan",
        "",
        f"Source: {report.source_name}",
        f"Verdict: {report.verdict}",
        "",
    ]
    if not actions:
        lines.extend(["No reviewer actions were generated.", ""])
        return "\n".join(lines)

    for action in actions:
        lines.extend(
            [
                f"## {action.id} - {action.title}",
                "",
                f"- Priority: {action.priority.upper()}",
                f"- Category: {action.category}",
                f"- Target: {action.target}",
                f"- Source: {source_reference(action.source_span)}",
                f"- Why it matters: {action.detail}",
                f"- Suggested fix: {action.suggested_fix}",
                "",
            ]
        )
        if action.source_span:
            lines.extend([f"> Source text: {action.source_span.text}", ""])
    return "\n".join(lines)


def deduplicate_actions(actions: list[ReviewerAction]) -> list[ReviewerAction]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[ReviewerAction] = []
    for action in sorted(actions, key=action_sort_key):
        key = (action.priority, action.category, action.target)
        if key in seen:
            continue
        seen.add(key)
        unique.append(action)
    return unique


def assign_action_ids(actions: list[ReviewerAction]) -> list[ReviewerAction]:
    assigned: list[ReviewerAction] = []
    for index, action in enumerate(actions, start=1):
        assigned.append(
            ReviewerAction(
                id=f"A{index}",
                priority=action.priority,
                category=action.category,
                title=action.title,
                target=action.target,
                detail=action.detail,
                suggested_fix=action.suggested_fix,
                source_span=action.source_span,
            )
        )
    return assigned


def action_sort_key(action: ReviewerAction) -> tuple[int, str, str]:
    priority_order = {"high": 0, "medium": 1, "low": 2}
    return (priority_order[action.priority], action.category, action.target)
