from app.aws.clients import _client_kwargs, get_client
from app.config import get_settings


def test_kwargs_omit_endpoint_when_unset(monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT_URL", "")
    get_settings.cache_clear()
    kwargs = _client_kwargs()
    assert "endpoint_url" not in kwargs
    assert kwargs["region_name"] == "us-east-1"


def test_kwargs_include_endpoint_when_set(monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    get_settings.cache_clear()
    kwargs = _client_kwargs()
    assert kwargs["endpoint_url"] == "http://localhost:4566"


def test_get_client_is_cached_per_service(aws):
    assert get_client("s3") is get_client("s3")


def test_get_client_differs_across_services(aws):
    assert get_client("s3") is not get_client("sts")
