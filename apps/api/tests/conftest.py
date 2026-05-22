import pytest

from app.api.routes.auth import reset_auth_rate_limiter
from app.core.config import settings

settings.database_url = "sqlite://"
settings.environment = "test"
settings.jwt_secret = "unit-test-jwt-secret"


@pytest.fixture(autouse=True)
def configure_test_settings() -> None:
    reset_auth_rate_limiter()
    settings.environment = "test"
    settings.jwt_secret = "unit-test-jwt-secret"
    settings.enable_test_admin = False
    settings.test_admin_account = ""
    settings.test_admin_password = ""
    settings.auth_rate_limit_max_attempts = 20
    settings.auth_rate_limit_window_seconds = 60
    yield
    reset_auth_rate_limiter()
