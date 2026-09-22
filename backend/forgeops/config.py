from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

MODEL_ROLES = ("supervisor", "specialist", "rca")


class Settings(BaseSettings):
    # Repo-root .env when running from backend/; container env vars override both.
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    forgeops_env: str = "development"
    database_url: str
    database_schema: str = "forgeops"
    forgeops_secret_key: SecretStr
    forgeops_admin_email: str
    forgeops_admin_password: SecretStr
    forgeops_workspace_name: str = "My workspace"
    cors_origins: list[str] = ["http://localhost:5173"]
    session_ttl_hours: int = 72

    # LLM (OpenRouter)
    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    forgeops_model_supervisor: str = "anthropic/claude-sonnet-5"
    forgeops_model_specialist: str = "anthropic/claude-haiku-4.5"
    forgeops_model_rca: str = "anthropic/claude-sonnet-5"

    # Time budgets in seconds (raise them for slow or free models)
    forgeops_specialist_seconds: float = 300
    forgeops_answer_seconds: float = 90
    forgeops_run_seconds: float = 1800

    # Knowledge vault search index location
    knowledge_data_dir: str = "../.forgeops-data/knowledge"
    # Operator-controlled folders that knowledge vaults must live inside (JSON list in .env).
    knowledge_vault_roots: list[str] = ["../knowledge-vault"]

    @property
    def is_production(self) -> bool:
        return self.forgeops_env == "production"

    def budgets(self):
        from forgeops.engine.budgets import Budgets

        return Budgets(specialist_seconds=self.forgeops_specialist_seconds,
                       answer_seconds=self.forgeops_answer_seconds, run_seconds=self.forgeops_run_seconds)

    def model_for(self, role: str) -> str:
        if role not in MODEL_ROLES:
            raise ValueError(f"Unknown model role {role!r}; expected one of {MODEL_ROLES}")
        return getattr(self, f"forgeops_model_{role}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
