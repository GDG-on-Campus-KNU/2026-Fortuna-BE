from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


PLACEHOLDER_SECRET_PREFIXES = ("change-", "replace-with-")


class Settings(BaseSettings):
    app_env: str = "local"
    cors_origins: str = "*"

    # DATABASE_URL should be an asynchronous connection string, e.g. postgresql+asyncpg://...
    DATABASE_URL: str

    # JWT security settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash"
    gemini_tts_model: str = "gemini-3.1-flash-tts-preview"
    gemini_tts_friendly_voice_name: str = "Puck"
    gemini_tts_professor_voice_name: str = "Kore"
    gemini_tts_sample_rate_hz: int = 24000
    gemini_tts_channels: int = 1
    gemini_tts_sample_width: int = 2

    tts_provider: str = "gemini"
    google_tts_language_code: str = "ko-KR"
    google_tts_voice_name: str | None = None
    google_tts_audio_encoding: str = "MP3"
    google_tts_speaking_rate: float = 1.0
    google_tts_pitch: float = 0.0

    storage_backend: str = "local"
    local_storage_dir: str = "storage"
    gcs_bucket_name: str | None = None
    gcs_signed_url_expiration_minutes: int = Field(default=60, ge=1)

    metadata_backend: str = "json"
    metadata_dir: str = "storage/metadata"
    max_upload_mb: int = Field(default=20, ge=0)
    public_base_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @computed_field
    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @computed_field
    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @computed_field
    @property
    def cors_allow_credentials(self) -> bool:
        return self.cors_origin_list != ["*"]

    @computed_field
    @property
    def local_storage_path(self) -> Path:
        return Path(self.local_storage_dir)

    @computed_field
    @property
    def metadata_path(self) -> Path:
        return Path(self.metadata_dir)

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    def validate_runtime_settings(self) -> None:
        if not self.JWT_SECRET_KEY.strip():
            raise RuntimeError("JWT_SECRET_KEY must be set.")
        if self.JWT_SECRET_KEY.startswith(PLACEHOLDER_SECRET_PREFIXES):
            raise RuntimeError("JWT_SECRET_KEY must not use an example placeholder.")
        if not self.DATABASE_URL.strip():
            raise RuntimeError("DATABASE_URL must be set.")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = Settings()
