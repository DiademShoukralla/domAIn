from domain.config import get_settings


def test_supervisor_and_chair_use_different_models() -> None:
    settings = get_settings()
    assert settings.supervisor_model != settings.council_chair_model
    assert settings.supervisor_model == "anthropic:claude-haiku-4-5"
