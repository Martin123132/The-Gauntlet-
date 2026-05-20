from __future__ import annotations

from gauntlet_core import analyze_paper_text
from gauntlet_core.repair_workshop import build_repair_steps, repair_status_counts, repair_workshop_to_markdown


def test_repair_steps_are_stable_and_sorted():
    report = analyze_paper_text("The paper resolves the paradox and eliminates the contradiction.", source_name="repair.txt")

    first = build_repair_steps(report)
    second = build_repair_steps(report)

    assert first
    assert [step.id for step in first] == [step.id for step in second]
    assert first[0].priority in {"high", "medium"}
    assert any("mechanism" in step.title.lower() or "evidence" in step.title.lower() for step in first)


def test_repair_steps_apply_saved_progress_and_export_markdown():
    report = analyze_paper_text("The paper resolves the paradox and eliminates the contradiction.", source_name="repair.txt")
    step = build_repair_steps(report)[0]
    progress = {
        step.id: {
            "status": "in-progress",
            "reviewer_note": "Add a mechanism paragraph before the evidence claim.",
            "updated_at": "2026-05-20T10:00:00+00:00",
        }
    }

    steps = build_repair_steps(report, progress)
    markdown = repair_workshop_to_markdown(report, steps)

    updated_step = next(item for item in steps if item.id == step.id)

    assert updated_step.status == "in-progress"
    assert updated_step.reviewer_note == "Add a mechanism paragraph before the evidence claim."
    assert repair_status_counts(steps)["in-progress"] == 1
    assert "# Repair Workshop: repair.txt" in markdown
    assert "Reviewer note: Add a mechanism paragraph" in markdown
    assert "Source text:" in markdown


def test_repair_workshop_handles_empty_report():
    report = analyze_paper_text("This note has background only.", source_name="empty.txt")
    steps = build_repair_steps(report)
    markdown = repair_workshop_to_markdown(report, steps)

    assert steps
    assert any(step.title == "State a testable resolution claim" for step in steps)
    assert "Repair Workshop" in markdown
