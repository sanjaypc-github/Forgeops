import pytest

from forgeops.config import Settings


def _settings(**kw):
    base = dict(database_url="postgresql+asyncpg://u:p@h/db", forgeops_secret_key="k",
                forgeops_admin_email="a@b.c", forgeops_admin_password="x")
    return Settings(_env_file=None, **(base | kw))


def test_model_defaults_and_roles():
    s = _settings()
    assert s.model_for("supervisor") == "anthropic/claude-sonnet-5"
    assert s.model_for("rca") == "anthropic/claude-sonnet-5"
    assert s.model_for("specialist") == "anthropic/claude-haiku-4.5"
    with pytest.raises(ValueError):
        s.model_for("unknown")


def test_openrouter_key_is_optional_and_secret():
    assert _settings().openrouter_api_key is None
    s = _settings(openrouter_api_key="sk-or-123")
    assert s.openrouter_api_key.get_secret_value() == "sk-or-123"
    assert "sk-or-123" not in repr(s)
