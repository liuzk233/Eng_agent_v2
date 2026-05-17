from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "vocabulary-story-learning-api"
    environment: str = "local"
    jwt_secret: str = ""
    database_url: str = ""
    db_pool_size: int = 20
    db_max_overflow: int = 40
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = ""
    celery_result_backend: str = ""
    test_admin_account: str = ""
    test_admin_password: str = ""
    enable_test_admin: bool = False
    auth_rate_limit_max_attempts: int = 20
    auth_rate_limit_window_seconds: int = 60
    cors_origins: str = ""
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_model: str = "qwen3.5-122b-a10b"

    model_config = SettingsConfigDict(
        env_prefix="VSL_",
        env_file=(_REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def require_jwt_secret(self) -> str:
        secret = self.jwt_secret.strip()
        if secret:
            return secret
        raise RuntimeError("VSL_JWT_SECRET must be configured")

    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def resolved_celery_broker_url(self) -> str:
        return self.celery_broker_url.strip() or self.redis_url

    def resolved_celery_result_backend(self) -> str:
        return self.celery_result_backend.strip() or self.redis_url


settings = Settings()
