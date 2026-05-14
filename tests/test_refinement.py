from gauntlet_core import analyze_paper_text
from gauntlet_core.refinement import RefinementError, run_refinement


class FakeClient:
    def __init__(self, provider: str, response: str):
        self.provider = provider
        self.response = response
        self.prompts = []

    def complete(self, prompt: str, model: str) -> str:
        self.prompts.append((prompt, model))
        return self.response


def test_refinement_uses_mocked_clients_and_rechecks_repair_plan():
    paper = """
    The paper resolves the paradox because the mechanism separates local and global scopes.
    The evidence section reports equation x = 1 and Smith et al. (2022) measurements.
    """
    report = analyze_paper_text(paper, source_name="paper.txt")
    openai = FakeClient(
        "OpenAI",
        "The weak point is evidence traceability. Concrete repair plan: link C1 to the equation and citation.",
    )
    anthropic = FakeClient(
        "Anthropic",
        "I disagree that the repair is complete; the scope boundary is still unsupported and needs a falsifiable check.",
    )

    refinement = run_refinement(
        report,
        paper,
        openai_api_key="session-openai",
        anthropic_api_key="session-anthropic",
        openai_client=openai,
        anthropic_client=anthropic,
    )

    assert refinement.openai_turn.response == openai.response
    assert refinement.anthropic_turn.response == anthropic.response
    assert refinement.disagreements
    assert refinement.recheck_report.verdict in {"RESOLVES", "PARTIAL", "FAILS", "CREATES_NEW_PARADOXES"}
    assert "The Gauntlet Refinement Report" in refinement.to_markdown()
    assert "session-openai" not in refinement.to_json()
    assert "session-anthropic" not in refinement.to_json()


def test_refinement_requires_keys_without_injected_clients():
    report = analyze_paper_text("The paper resolves the paradox.")

    try:
        run_refinement(report, "The paper resolves the paradox.", "", "")
    except RefinementError as exc:
        assert "OpenAI API key is required" in str(exc)
    else:
        raise AssertionError("Expected RefinementError")
