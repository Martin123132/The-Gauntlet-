from __future__ import annotations

from gauntlet_core import analyze_paper_text
from gauntlet_core.repair_workshop import build_repair_steps
from gauntlet_core.revision_recheck import (
    recheck_repair_revision,
    revision_recheck_counts,
    revision_recheck_log_to_markdown,
)


def test_revision_recheck_marks_better_mechanism_as_improved():
    report = analyze_paper_text("The paper resolves the paradox and eliminates the contradiction.", source_name="revision.txt")
    step = next(item for item in build_repair_steps(report) if "mechanism" in item.title.lower())

    result = recheck_repair_revision(
        report,
        step,
        "The paper resolves the paradox because a bounded mechanism separates local and global cases through equation x = y + 2.",
    )

    assert result.status == "improved"
    assert result.step_id == step.id
    assert result.revised_text
    assert result.revised_gap_count <= result.original_gap_count


def test_revision_recheck_catches_still_weak_revision():
    report = analyze_paper_text("The paper resolves the paradox and eliminates the contradiction.", source_name="revision.txt")
    step = build_repair_steps(report)[0]

    result = recheck_repair_revision(report, step, "It is fixed.")

    assert result.status == "still-weak"
    assert "still needs work" in result.summary


def test_revision_recheck_log_exports_saved_results():
    report = analyze_paper_text("The paper resolves the paradox and eliminates the contradiction.", source_name="revision.txt")
    step = build_repair_steps(report)[0]
    result = recheck_repair_revision(
        report,
        step,
        "The paper resolves the paradox because a specific mechanism links the contradiction to 12 measured observations.",
    )
    payload = {step.id: result.to_dict()}

    markdown = revision_recheck_log_to_markdown(report, payload)

    assert revision_recheck_counts(payload)[result.status] == 1
    assert "# Revision Re-Check Log: revision.txt" in markdown
    assert "Original Snippet" in markdown
    assert "Revised Snippet" in markdown
    assert "full uploaded paper" in markdown
