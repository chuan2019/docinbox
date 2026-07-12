import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from app.aws.clients import get_client
from app.config import get_settings


@pytest.fixture(autouse=True)
def _aws_env(monkeypatch):
    """Point Settings at fake, region-only AWS config for every test.

    An empty string beats whatever's in .env (env vars outrank the dotenv
    file), so boto3 targets its normal AWS endpoints -- the ones moto
    intercepts -- instead of a real MiniStack instance.
    """
    monkeypatch.setenv("AWS_ENDPOINT_URL", "")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")

    get_settings.cache_clear()
    get_client.cache_clear()
    yield
    get_settings.cache_clear()
    get_client.cache_clear()


@pytest.fixture
def aws():
    """Activate moto's AWS mock for tests that make real boto3 calls."""
    with mock_aws():
        yield


@pytest.fixture
def client(aws):
    """FastAPI TestClient wired to the moto-mocked AWS backend."""
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
