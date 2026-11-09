"""
Application configuration — all settings loaded from environment variables.
Fails fast at startup if required variables are missing.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "production", "test"] = "development"
    app_secret_key: str = "dev-secret-key-not-for-production"
    cors_allowed_origins: list[str] = ["http://localhost:5173"]

    # Database
    database_url: str = "sqlite+aiosqlite:///./trustvault_dev.db"
    database_url_sync: str = ""

    # Keycloak OIDC (not used in dev mode)
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "trustvault"
    keycloak_client_id: str = "trustvault-api"
    keycloak_client_secret: str = ""

    # MinIO / S3-compatible object storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "devaccess"
    minio_secret_key: str = "devsecret"
    minio_bucket: str = "trustvault-documents"
    minio_secure: bool = False

    # Encryption KEK
    encryption_kek: str = "ZpUr9hyezdNIfAW9ptiwezrLOUWLU/EwYB0WGGhWjKw="
    encryption_kek_version: str = "v1"

    # ClamAV (optional)
    clamav_enabled: bool = False
    clamav_host: str = "clamav"
    clamav_port: int = 3310

    # Ollama (optional)
    ollama_enabled: bool = False
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2"

    # Upload limits
    max_upload_size_bytes: int = 50 * 1024 * 1024
    allowed_extensions: list[str] = [
        "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt",
        "txt", "csv", "png", "jpg", "jpeg", "gif", "webp",
        "zip", "tar", "gz",
    ]

    # Token settings
    access_token_expire_minutes: int = 60
    jwks_cache_ttl_seconds: int = 300

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Audit
    audit_fail_closed: bool = False

    # Dev mode — use local filesystem instead of MinIO, simple JWT instead of Keycloak
    use_local_storage: bool = True
    local_storage_path: str = "./dev_storage"
    dev_auth_enabled: bool = True

    @model_validator(mode="after")
    def derive_sync_url(self) -> "Settings":
        if not self.database_url_sync:
            if "sqlite" in self.database_url:
                self.database_url_sync = self.database_url.replace(
                    "sqlite+aiosqlite://", "sqlite://"
                )
            else:
                self.database_url_sync = self.database_url.replace(
                    "postgresql+asyncpg://", "postgresql+psycopg2://"
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def keycloak_issuer(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"

    @property
    def keycloak_jwks_uri(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/certs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
