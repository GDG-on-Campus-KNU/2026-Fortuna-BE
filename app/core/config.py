import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # DATABASE_URL should be an asynchronous connection string, e.g. postgresql+asyncpg://...
    DATABASE_URL: str = ""

    # JWT security settings
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
