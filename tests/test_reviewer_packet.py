from __future__ import annotations

from io import BytesIO
import json
from zipfile import ZipFile

from gauntlet_core.analysis import analyze_paper_text
from gauntlet_core.repair_workshop import build_repair_steps
from gauntlet_core.reviewer_packet import (
    build_reviewer_packet_bundle,
    reviewer_packet_to_html,
    reviewer_packet_to_markdown,
)
from gauntlet_core.source_review import build_source_review_items


def packet_report():
    return analyze_paper_text(
        "Abstract\n"
        "This paper resolves the time paradox for every possible frame. "
        "The mechanism is complete because the model defines the model. "
        "However, the method does not resolve the same paradox in edge cases. "
        "We include 12 observations and a measured benchmark.",
        source_name="reviewer-packet-paper.txt",
    )


def test_reviewer_packet_markdown_includes_review_state_and_privacy_note():
    report = packet_report()
    issue = build_source_review_items(report)[0]
    step = build_repair_steps(report)[0]
    markdown = reviewer_packet_to_markdown(
        report,
        issue_reviews={
            issue.id: {
                "status": "confirmed",
                "reviewer_note": "Confirmed by reviewer.",
                "updated_at": "2026-05-24T10:00:00+00:00",
            }
        },
        repair_progress={
            step.id: {
                "status": "in-progress",
                "reviewer_note": "Drafting a scoped mechanism.",
                "updated_at": "2026-05-24T10:05:00+00:00",
            }
        },
        revision_rechecks={
            step.id: {
                "id": "RC1",
                "step_id": step.id,
                "status": "still-weak",
                "checked_at": "2026-05-24T10:10:00+00:00",
                "original_text": "The old claim resolves everything.",
                "revised_text": "The revised claim is scoped but still lacks evidence.",
                "summary": "The revision still needs stronger evidence.",
            }
        },
    )

    assert "# Reviewer Packet: reviewer-packet-paper.txt" in markdown
    assert "## Claim-Evidence Map" in markdown
    assert "## Repair Workshop Checklist" in markdown
    assert "## Revision Re-Check Log" in markdown
    assert "Review status: Confirmed" in markdown
    assert "Confirmed by reviewer." in markdown
    assert "Drafting a scoped mechanism." in markdown
    assert "The revision still needs stronger evidence." in markdown
    assert "do not include the full uploaded paper file or API keys" in markdown


def test_reviewer_packet_html_escapes_reviewer_notes():
    report = packet_report()
    issue = build_source_review_items(report)[0]
    html = reviewer_packet_to_html(
        report,
        issue_reviews={
            issue.id: {
                "status": "false-positive",
                "reviewer_note": "<script>alert('x')</script>",
            }
        },
    )

    assert "Reviewer Packet" in html
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;" in html
    assert "<script>alert('x')</script>" not in html


def test_reviewer_packet_bundle_contains_packet_files_without_full_report_json():
    report = packet_report()
    bundle = build_reviewer_packet_bundle(
        report,
        issue_reviews={"F1": {"status": "resolved", "reviewer_note": "Checked."}},
    )

    with ZipFile(BytesIO(bundle)) as archive:
        names = set(archive.namelist())
        assert "reviewer-packet-paper-reviewer-packet.md" in names
        assert "reviewer-packet-paper-reviewer-packet.html" in names
        assert "reviewer-packet-paper-review-state.json" in names
        assert "README.txt" in names
        assert all(not name.endswith("-gauntlet-report.json") for name in names)
        state = json.loads(archive.read("reviewer-packet-paper-review-state.json").decode("utf-8"))
        readme = archive.read("README.txt").decode("utf-8")

    assert state["issue_reviews"]["F1"]["status"] == "resolved"
    assert "full uploaded paper file or API keys" in readme
    assert "api_key" not in readme.lower()
