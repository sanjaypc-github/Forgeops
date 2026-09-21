from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Repo-root .env when running from backend/; container env vars override both.
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    forgeops_env: str = "development"
    database_url: str
    forgeops_secret_key: SecretStr
    forgeops_admin_email: str
    forgeops_admin_password: SecretStr
    forgeops_workspace_name: str = "My workspace"
    cors_origins: list[str] = ["http://localhost:5173"]
    session_ttl_hours: int = 72

    @property
    def is_production(self) -> bool:
        return self.forgeops_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
