import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # DATABASE_URL should be an asynchronous connection string, e.g. postgresql+asyncpg://...
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fortuna"

    # JWT security settings
    JWT_SECRET_KEY: str = (
        "94c16a1c8651079541a774dbba22cb33be8ebc7f9994c65e8a5b29381c8ee90d"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
