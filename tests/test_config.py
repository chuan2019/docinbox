from app.config import Settings, get_settings


def test_defaults_leave_endpoint_unset_for_real_aws(monkeypatch):
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    settings = Settings(_env_file=None)
    assert settings.aws_endpoint_url is None
    assert settings.aws_region == "us-east-1"


def test_endpoint_override_is_read_from_env(monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    settings = Settings()
    assert settings.aws_endpoint_url == "http://localhost:4566"


def test_get_settings_is_cached():
    assert get_settings() is get_settings()
