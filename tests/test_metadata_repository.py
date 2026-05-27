from typing import Protocol

import pytest

from app.core.config import Settings
from app.infra.repositories.json_repo import JsonMetadataRepository
from app.infra.repositories.postgres import PostgresMetadataRepository


class MetadataRepository(Protocol):
    def save_file(self, record: dict) -> dict: ...

    def get_file(self, file_id: str, user_id: str | None = None) -> dict | None: ...

    def list_files(self, user_id: str) -> list[dict]: ...

    def save_script(self, record: dict) -> dict: ...

    def get_script(self, script_id: str, user_id: str | None = None) -> dict | None: ...

    def list_scripts(self, user_id: str) -> list[dict]: ...

    def save_audio(self, record: dict) -> dict: ...

    def get_audio(self, audio_id: str, user_id: str | None = None) -> dict | None: ...

    def list_audio(self, user_id: str) -> list[dict]: ...

    def save_job(self, record: dict) -> dict: ...

    def update_job(
        self, job_id: str, user_id: str | None, changes: dict
    ) -> dict | None: ...

    def get_job(self, job_id: str, user_id: str | None = None) -> dict | None: ...

    def list_jobs(self, user_id: str) -> list[dict]: ...


@pytest.fixture(params=["json", "postgres"])
def repository(request: pytest.FixtureRequest, tmp_path) -> MetadataRepository:
    if request.param == "json":
        return JsonMetadataRepository(tmp_path / "metadata")
    settings = Settings(
        DATABASE_URL=f"sqlite:///{(tmp_path / 'metadata.db').as_posix()}",
        _env_file=None,
    )
    return PostgresMetadataRepository(settings)


def test_metadata_repository_contract(repository: MetadataRepository) -> None:
    user_id = "user_1"
    other_user_id = "user_2"
    file_record = {
        "file_id": "file_1",
        "user_id": user_id,
        "filename": "note.txt",
        "content_type": "text/plain",
        "size": 12,
        "storage_uri": "local://uploads/user_1/file_1/original.txt",
        "extracted_text_uri": "local://uploads/user_1/file_1/extracted.txt",
        "extracted_text_chars": 12,
        "created_at": "2026-05-25T00:00:00+00:00",
    }
    script_record = {
        "script_id": "script_1",
        "user_id": user_id,
        "file_id": "file_1",
        "script": "Generated script",
        "metadata": {"duration_minutes": 10, "format": "dialogue"},
        "prompt_chars": 123,
        "storage_uri": "local://scripts/user_1/script_1.json",
        "created_at": "2026-05-25T00:01:00+00:00",
    }
    audio_record = {
        "audio_id": "audio_1",
        "user_id": user_id,
        "script_id": "script_1",
        "audio_url": "/static/audio/user_1/audio_1.wav",
        "audio_format": "wav",
        "media_type": "audio/wav",
        "voice_style": "friendly",
        "speed": "normal",
        "metadata": {"provider": "gemini"},
        "storage_uri": "local://audio/user_1/audio_1.wav",
        "created_at": "2026-05-25T00:02:00+00:00",
    }
    job_record = {
        "job_id": "job_1",
        "user_id": user_id,
        "status": "pending",
        "step": "queued",
        "progress": 0,
        "content_id": None,
        "error": None,
        "input": {"file_id": "file_1"},
        "created_at": "2026-05-25T00:03:00+00:00",
        "updated_at": "2026-05-25T00:03:00+00:00",
    }

    assert repository.save_file(file_record) == file_record
    assert repository.save_script(script_record) == script_record
    assert repository.save_audio(audio_record) == audio_record
    assert repository.save_job(job_record) == job_record

    assert repository.get_file("file_1", user_id) == file_record
    assert repository.get_file("file_1", other_user_id) is None
    assert repository.list_files(user_id) == [file_record]
    assert repository.list_files(other_user_id) == []

    assert repository.get_script("script_1", user_id) == script_record
    assert repository.list_scripts(user_id) == [script_record]

    assert repository.get_audio("audio_1", user_id) == audio_record
    assert repository.list_audio(user_id) == [audio_record]

    updated = repository.update_job(
        "job_1",
        user_id,
        {"status": "running", "step": "generating_script", "progress": 40},
    )
    assert updated is not None
    assert updated["status"] == "running"
    assert updated["step"] == "generating_script"
    assert updated["progress"] == 40
    assert updated["input"] == {"file_id": "file_1"}
    assert repository.update_job("job_1", other_user_id, {"status": "failed"}) is None
    assert repository.get_job("job_1", user_id) == updated
    assert repository.list_jobs(user_id) == [updated]


def test_postgres_repository_uses_sync_psycopg_url() -> None:
    repository = PostgresMetadataRepository.__new__(PostgresMetadataRepository)

    assert (
        repository._sync_database_url("postgresql://user:pw@localhost:5432/fortuna")
        == "postgresql+psycopg://user:pw@localhost:5432/fortuna"
    )
    assert (
        repository._sync_database_url(
            "postgresql+asyncpg://user:pw@localhost:5432/fortuna"
        )
        == "postgresql+psycopg://user:pw@localhost:5432/fortuna"
    )
