from gauntlet_core import analyze_paper_text
from gauntlet_core.refinement import (
    ProviderSelection,
    RefinementError,
    extract_gemini_text,
    run_provider_refinement,
    run_refinement,
)


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

    assert refinement.critic_turn.response == openai.response
    assert refinement.challenger_turn.response == anthropic.response
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


def test_provider_refinement_supports_gemini_without_saving_keys():
    paper = """
    The paper resolves the information paradox by using a scoped mechanism.
    The evidence includes a derivation, a falsifiable prediction, and Lee et al. (2024).
    """
    report = analyze_paper_text(paper, source_name="gemini-paper.txt")
    gemini = FakeClient(
        "Gemini",
        "The repair should preserve the scoped mechanism but add evidence traceability for each claim.",
    )
    openai = FakeClient(
        "OpenAI",
        "The first repair missed one unsupported assumption; the remaining tension is test design.",
    )

    refinement = run_provider_refinement(
        report,
        paper,
        critic=ProviderSelection("critic", "Gemini", "gemini-2.5-flash", "session-gemini"),
        challenger=ProviderSelection("challenger", "OpenAI", "gpt-4.1", "session-openai"),
        clients={"critic": gemini, "challenger": openai},
    )

    assert refinement.critic_turn.provider == "Gemini"
    assert refinement.challenger_turn.provider == "OpenAI"
    assert "Gemini Critique" in refinement.to_markdown()
    assert "OpenAI Challenge" in refinement.to_markdown()
    assert "session-gemini" not in refinement.to_json()
    assert "session-openai" not in refinement.to_json()


def test_provider_refinement_can_use_one_gemini_key_for_both_roles():
    report = analyze_paper_text("The paper resolves the paradox through a measured mechanism.")
    critic = FakeClient("Gemini", "The mechanism needs a clearer citation.")
    challenger = FakeClient("Gemini", "The first critique missed weak falsifiability and unsupported scope.")

    refinement = run_provider_refinement(
        report,
        "The paper resolves the paradox through a measured mechanism.",
        critic=ProviderSelection("critic", "Gemini", "gemini-2.5-flash", "session-gemini"),
        challenger=ProviderSelection("challenger", "Gemini", "gemini-2.5-flash", "session-gemini"),
        clients={"critic": critic, "challenger": challenger},
    )

    assert [turn.provider for turn in refinement.turns] == ["Gemini", "Gemini"]
    assert "session-gemini" not in refinement.to_json()


def test_extract_gemini_text_reads_direct_text():
    class GeminiResponse:
        text = " visible Gemini message "

    assert extract_gemini_text(GeminiResponse()) == "visible Gemini message"
