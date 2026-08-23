"""Tests for application configuration."""

import pytest

from thermalshift.config import Settings


def test_default_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FORTYGUARD_BASE_URL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.fortyguard_base_url == "https://api.fortyguard.com"


@pytest.mark.parametrize("api_key", [None, "", "   "])
def test_missing_or_blank_api_key_raises(api_key: str | None) -> None:
    settings = Settings(fortyguard_api_key=api_key, _env_file=None)

    with pytest.raises(RuntimeError, match="FORTYGUARD_API_KEY is required"):
        settings.require_fortyguard_api_key()


def test_configured_api_key_can_be_retrieved() -> None:
    settings = Settings(fortyguard_api_key="test-api-key", _env_file=None)

    assert settings.require_fortyguard_api_key().get_secret_value() == "test-api-key"


def test_secret_representation_does_not_expose_key() -> None:
    api_key = "test-api-key"
    settings = Settings(fortyguard_api_key=api_key, _env_file=None)

    assert api_key not in repr(settings.fortyguard_api_key)
    assert api_key not in str(settings.fortyguard_api_key)
