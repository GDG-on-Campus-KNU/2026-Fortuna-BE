import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.deps import get_current_user_id
from main import app


def test_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_invalid_script_option_returns_consistent_error() -> None:
    app.dependency_overrides[get_current_user_id] = lambda: "test-user-id"
    client = TestClient(app)

    try:
        response = client.post(
            "/jobs",
            json={
                "file_id": "file_1",
                "duration_minutes": 7,
                "format": "summary",
                "detail_level": "normal",
                "voice_style": "friendly",
                "speed": "normal",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_OPTION"


def test_podcast_api_requires_bearer_token() -> None:
    client = TestClient(app)

    response = client.post(
        "/jobs",
        json={
            "file_id": "file_1",
            "duration_minutes": 10,
            "format": "summary",
            "detail_level": "normal",
            "voice_style": "friendly",
            "speed": "normal",
        },
    )

    assert response.status_code == 401


def test_default_settings_are_safe_for_local_cors_and_gemini() -> None:
    settings = Settings(_env_file=None)

    assert settings.gemini_model == "gemini-3.5-flash"
    assert settings.gemini_tts_model == "gemini-3.1-flash-tts-preview"
    assert settings.tts_provider == "gemini"
    assert settings.cors_origin_list == ["*"]
    assert settings.cors_allow_credentials is False
    assert Settings(cors_origins="http://localhost:5173", _env_file=None).cors_allow_credentials is True


def test_env_example_loads_without_type_errors() -> None:
    settings = Settings(_env_file=".env.example")

    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.JWT_ALGORITHM == "HS256"
    assert settings.JWT_SECRET_KEY


def test_runtime_settings_reject_example_jwt_secret() -> None:
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
        JWT_SECRET_KEY="replace-with-a-generated-secret",
        _env_file=None,
    )

    try:
        settings.validate_runtime_settings()
    except RuntimeError as exc:
        assert "JWT_SECRET_KEY" in str(exc)
    else:
        raise AssertionError("example JWT secret should be rejected at runtime")


def test_examples_and_docs_do_not_contain_real_secrets() -> None:
    checked_paths = [
        Path(".env.example"),
        Path(".env.docker.example"),
        Path("README.md"),
        Path("docker-compose.yml"),
    ]
    secret_patterns = {
        "google_api_key": re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
        "private_key_block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        "service_account_private_key": re.compile(r'"private_key"\s*:'),
        "service_account_email": re.compile(r'"client_email"\s*:'),
        "hex_secret": re.compile(r"\b[0-9a-fA-F]{64}\b"),
        "old_jwt_placeholder": re.compile("change" + r"-me-generate"),
    }

    for path in checked_paths:
        content = path.read_text(encoding="utf-8")
        for name, pattern in secret_patterns.items():
            assert not pattern.search(content), f"{path} contains {name}"
