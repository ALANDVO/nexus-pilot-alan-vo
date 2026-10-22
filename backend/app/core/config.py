from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    env: str = Field(default="development", alias="ENV")
    secret_key: str = Field(default="dev-secret-change-in-production", alias="SECRET_KEY")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    frontend_url: str = Field(default="http://127.0.0.1:5173", alias="FRONTEND_URL")

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./data/app.db", alias="DATABASE_URL")

    # Keycloak OIDC
    keycloak_url: str = Field(default="http://127.0.0.1:8080", alias="KEYCLOAK_URL")
    keycloak_realm: str = Field(default="nexus-pilot", alias="KEYCLOAK_REALM")
    keycloak_client_id: str = Field(default="nexus-pilot-client", alias="KEYCLOAK_CLIENT_ID")
    keycloak_client_secret: str = Field(default="", alias="KEYCLOAK_CLIENT_SECRET")
    keycloak_admin_user: str = Field(default="admin", alias="KEYCLOAK_ADMIN_USER")
    keycloak_admin_password: str = Field(default="admin", alias="KEYCLOAK_ADMIN_PASSWORD")

    # LLM (optional)
    llm_api_key: Optional[str] = Field(default=None, alias="LLM_API_KEY")
    llm_provider: Optional[str] = Field(default="openai-compatible", alias="LLM_PROVIDER")
    llm_model: Optional[str] = Field(default=None, alias="LLM_MODEL")
    llm_base_url: Optional[str] = Field(default=None, alias="LLM_BASE_URL")

    # CAD Processing
    max_step_size_mb: int = Field(default=500, alias="MAX_STEP_SIZE_MB")
    memory_envelope_mb: int = Field(default=1024, alias="MEMORY_ENVELOPE_MB")

    @property
    def keycloak_issuer(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"

    @property
    def keycloak_jwks_url(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/certs"

    @property
    def keycloak_auth_url(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/auth"

    @property
    def keycloak_token_url(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/token"

    @property
    def keycloak_logout_url(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/logout"

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def demo_mode_allowed(self) -> bool:
        return not self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()