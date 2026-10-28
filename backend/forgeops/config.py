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

    # "openrouter" for the real provider, "offline" for the labelled development stand-in
    forgeops_llm: str = "openrouter"

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
    # Context discipline: how many recent tool results each desk keeps in full
    forgeops_keep_full_tool_outputs: int = 3
    forgeops_empty_results_before_stop: int = 2
    forgeops_tool_output_chars: int = 8000
    # Ask the provider to cache the stable prompt prefix (paid models; free ones ignore it)
    forgeops_prompt_cache: bool = False

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
                       answer_seconds=self.forgeops_answer_seconds, run_seconds=self.forgeops_run_seconds,
                       tool_output_chars=self.forgeops_tool_output_chars,
                       keep_full_tool_outputs=self.forgeops_keep_full_tool_outputs,
                       empty_results_before_stop=self.forgeops_empty_results_before_stop)

    def model_for(self, role: str) -> str:
        if role not in MODEL_ROLES:
            raise ValueError(f"Unknown model role {role!r}; expected one of {MODEL_ROLES}")
        return getattr(self, f"forgeops_model_{role}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
