import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def auth_mode_for_tests(request):
    previous = settings.auth_required
    settings.auth_required = request.module.__name__.endswith("test_auth_api")
    yield
    settings.auth_required = previous
