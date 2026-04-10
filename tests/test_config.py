import os
import pytest


def test_settings_loads_required_vars():
    from app.config import Settings
    s = Settings(_env_file=None)
    assert s.claude_api_key == "test-claude-key"
    assert s.recaptcha_v3_secret_key == "test-v3-secret"
    assert s.recaptcha_v2_secret_key == "test-v2-secret"


def test_settings_defaults():
    from app.config import Settings
    s = Settings(_env_file=None)
    assert s.daily_token_budget == 50000
    assert s.default_personality == "casual"


def test_origins_list_parses_comma_separated():
    from app.config import Settings
    s = Settings(
        _env_file=None,
        claude_api_key="k",
        recaptcha_v3_secret_key="v3",
        recaptcha_v2_secret_key="v2",
        allowed_origins="https://example.com,http://localhost:3000",
    )
    assert s.origins_list == ["https://example.com", "http://localhost:3000"]


def test_origins_list_single_entry():
    from app.config import Settings
    s = Settings(
        _env_file=None,
        claude_api_key="k",
        recaptcha_v3_secret_key="v3",
        recaptcha_v2_secret_key="v2",
        allowed_origins="https://example.com",
    )
    assert s.origins_list == ["https://example.com"]


def test_missing_required_var_raises():
    from pydantic import ValidationError
    from app.config import Settings
    # Temporarily remove CLAUDE_API_KEY from environment to test validation
    original_key = os.environ.pop("CLAUDE_API_KEY", None)
    try:
        with pytest.raises(ValidationError):
            Settings(
                _env_file=None,
                recaptcha_v3_secret_key="v3",
                recaptcha_v2_secret_key="v2",
                # claude_api_key deliberately omitted
            )
    finally:
        if original_key is not None:
            os.environ["CLAUDE_API_KEY"] = original_key


def test_origins_list_strips_whitespace():
    from app.config import Settings
    s = Settings(
        _env_file=None,
        claude_api_key="k",
        recaptcha_v3_secret_key="v3",
        recaptcha_v2_secret_key="v2",
        allowed_origins=" https://a.com , https://b.com ",
    )
    assert s.origins_list == ["https://a.com", "https://b.com"]


def test_origins_list_ignores_trailing_comma():
    from app.config import Settings
    s = Settings(
        _env_file=None,
        claude_api_key="k",
        recaptcha_v3_secret_key="v3",
        recaptcha_v2_secret_key="v2",
        allowed_origins="https://a.com,",
    )
    assert s.origins_list == ["https://a.com"]
