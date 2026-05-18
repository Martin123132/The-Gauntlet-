from __future__ import annotations

from gauntlet_core import action_plan_to_markdown, analyze_paper_text, build_reviewer_action_plan


def test_action_plan_prioritizes_claim_repairs():
    report = analyze_paper_text(
        "The theory resolves the paradox. The model explains it because the model says it is solved.",
        source_name="weak-paper.txt",
    )

    actions = build_reviewer_action_plan(report)
    markdown = action_plan_to_markdown(report)

    assert actions
    assert actions[0].id == "A1"
    assert any(action.priority in {"high", "medium"} for action in actions)
    assert any("mechanism" in action.title.lower() or "evidence" in action.title.lower() for action in actions)
    assert "Reviewer Action Plan" in markdown
    assert "Suggested fix" in markdown


def test_action_plan_handles_no_claims():
    report = analyze_paper_text(
        "This short note describes background context without a clear resolution.",
        source_name="no-claims.txt",
    )

    actions = build_reviewer_action_plan(report)

    assert any(action.title == "State a testable resolution claim" for action in actions)
