"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ThermalShift configuration sourced from the environment and optional .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    fortyguard_api_key: SecretStr | None = None
    fortyguard_base_url: str = "https://api.fortyguard.com"

    def require_fortyguard_api_key(self) -> SecretStr:
        """Return the FortyGuard API key or raise when it is missing or blank."""
        if (
            self.fortyguard_api_key is None
            or not self.fortyguard_api_key.get_secret_value().strip()
        ):
            raise RuntimeError("FORTYGUARD_API_KEY is required but is missing or blank")
        return self.fortyguard_api_key


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
