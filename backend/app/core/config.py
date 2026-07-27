from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/eter_erp"
    environment: str = "development"
    auth_required: bool = True
    auth_secret_key: str = "dev-only-change-me-before-beta"
    session_cookie_name: str = "eter_erp_session"
    session_duration_minutes: int = 60 * 8
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cors_allowed_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    frontend_public_url: str = "http://localhost:3000"
    initial_admin_email: str | None = Field(default=None)
    initial_admin_password: str | None = Field(default=None)
    initial_admin_name: str = "Administrador"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_beta_security(self):
        if self.environment in {"beta", "production"}:
            if self.auth_secret_key == "dev-only-change-me-before-beta" or len(self.auth_secret_key) < 32:
                raise ValueError("AUTH_SECRET_KEY debe configurarse con un valor seguro antes de beta/produccion.")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE debe ser true en beta/produccion.")
            if not self.cors_origins:
                raise ValueError("CORS_ALLOWED_ORIGINS debe incluir al menos un origen permitido.")
        return self


settings = Settings()
