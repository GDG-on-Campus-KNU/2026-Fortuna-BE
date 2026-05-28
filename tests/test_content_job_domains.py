from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.deps import (
    get_content_job_processor,
    get_current_user_id,
    get_job_service,
    get_source_service,
)
from app.domain.content.service import ContentService
from app.domain.job.service import JobService
from app.domain.source.service import SourceService
from app.infra.pdf.extractor import PDFExtractor
from app.infra.repositories.json_repo import JsonMetadataRepository
from app.infra.storage.local import LocalStorageService
from main import app


class NoopContentJobProcessor:
    def process(self, user_id: str, job_id: str) -> None:
        return None


def test_job_create_and_lookup(tmp_path) -> None:
    metadata = JsonMetadataRepository(tmp_path / "metadata")
    settings = Settings(
        app_env="test",
        local_storage_dir=str(tmp_path / "storage"),
        metadata_dir=str(tmp_path / "metadata"),
        _env_file=None,
    )
    storage = LocalStorageService(settings)
    source_service = SourceService(
        settings=settings,
        storage=storage,
        repository=metadata,
        text_extractor=PDFExtractor(),
    )
    app.dependency_overrides[get_current_user_id] = lambda: "test-user-id"
    app.dependency_overrides[get_job_service] = lambda: JobService(metadata)
    app.dependency_overrides[get_source_service] = lambda: source_service
    app.dependency_overrides[get_content_job_processor] = lambda: NoopContentJobProcessor()
    client = TestClient(app)

    try:
        upload = client.post(
            "/uploads",
            files={"file": ("note.txt", b"content", "text/plain")},
        )
        assert upload.status_code == 200
        file_id = upload.json()["file_id"]

        response = client.post(
            "/jobs",
            json={
                "file_id": file_id,
                "duration_minutes": 10,
                "format": "summary",
                "detail_level": "normal",
                "voice_style": "friendly",
                "speed": "normal",
            },
        )

        assert response.status_code == 202
        created = response.json()
        assert created["status"] == "pending"
        assert created["step"] == "queued"
        assert created["progress"] == 0
        assert created["input"]["filename"] == "note.txt"

        lookup = client.get(f"/jobs/{created['job_id']}")

        assert lookup.status_code == 200
        assert lookup.json()["job_id"] == created["job_id"]
        assert lookup.json()["input"]["file_id"] == file_id
        job_record = metadata.get_job(created["job_id"], "test-user-id")
        file_id = job_record["input"]["file_id"]
        assert metadata.get_file(file_id, "test-user-id")["filename"] == "note.txt"
        assert job_record["input"]["content_type"] == "text/plain"
        assert job_record["input"]["extracted_text_chars"] > 0
    finally:
        app.dependency_overrides.clear()


def test_job_rejects_unknown_file_id(tmp_path) -> None:
    metadata = JsonMetadataRepository(tmp_path / "metadata")
    app.dependency_overrides[get_current_user_id] = lambda: "test-user-id"
    app.dependency_overrides[get_job_service] = lambda: JobService(metadata)
    app.dependency_overrides[get_content_job_processor] = lambda: NoopContentJobProcessor()
    client = TestClient(app)

    try:
        response = client.post(
            "/jobs",
            json={
                "file_id": "file_missing",
                "duration_minutes": 10,
                "format": "summary",
                "detail_level": "normal",
                "voice_style": "friendly",
                "speed": "normal",
            },
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FILE_NOT_FOUND"
        assert metadata.list_jobs("test-user-id") == []
    finally:
        app.dependency_overrides.clear()


def test_content_service_assembles_audio_content(tmp_path) -> None:
    metadata = JsonMetadataRepository(tmp_path / "metadata")
    user_id = "user_1"
    metadata.save_file({"file_id": "file_1", "user_id": user_id, "filename": "note.txt"})
    metadata.save_script(
        {
            "script_id": "script_1",
            "user_id": user_id,
            "file_id": "file_1",
            "script": "Generated script",
            "metadata": {"duration_minutes": 10},
        }
    )
    metadata.save_audio(
        {
            "audio_id": "audio_1",
            "user_id": user_id,
            "script_id": "script_1",
            "audio_url": "/static/audio/user_1/audio_1.wav",
            "voice_style": "friendly",
            "speed": "normal",
            "created_at": "2026-05-25T00:00:00+00:00",
        }
    )
    service = ContentService(metadata)

    contents = service.list_contents(user_id)
    content = service.get_content(user_id, "audio_1")

    assert contents[0]["content_id"] == "audio_1"
    assert content["filename"] == "note.txt"
    assert content["script"] == "Generated script"
    assert content["metadata"]["tts"]["speed"] == "normal"


def test_content_service_refreshes_audio_url_from_storage_uri(tmp_path) -> None:
    class FakeAudioUrlResolver:
        def resolve_audio_url(self, storage_uri: str, fallback_url: str) -> str:
            assert storage_uri == "gs://bucket/audio/user_1/audio_1.wav"
            assert fallback_url == "expired-url"
            return "fresh-signed-url"

    metadata = JsonMetadataRepository(tmp_path / "metadata")
    user_id = "user_1"
    metadata.save_file({"file_id": "file_1", "user_id": user_id, "filename": "note.txt"})
    metadata.save_script(
        {
            "script_id": "script_1",
            "user_id": user_id,
            "file_id": "file_1",
            "script": "Generated script",
            "metadata": {},
        }
    )
    metadata.save_audio(
        {
            "audio_id": "audio_1",
            "user_id": user_id,
            "script_id": "script_1",
            "audio_url": "expired-url",
            "storage_uri": "gs://bucket/audio/user_1/audio_1.wav",
            "created_at": "2026-05-25T00:00:00+00:00",
        }
    )
    service = ContentService(metadata, audio_url_resolver=FakeAudioUrlResolver())

    content = service.get_content(user_id, "audio_1")

    assert content["audio_url"] == "fresh-signed-url"


def test_job_status_transitions(tmp_path) -> None:
    metadata = JsonMetadataRepository(tmp_path / "metadata")
    service = JobService(metadata)
    job = service.create_job(
        user_id="user_1",
        file_id="file_1",
        filename="note.txt",
        content_type="text/plain",
        file_size=12,
        extracted_text_chars=12,
        duration_minutes=10,
        script_format="summary",
        detail_level="normal",
        voice_style="friendly",
        speed="normal",
    )

    running = service.mark_running("user_1", job["job_id"], "generating_script", 40)
    done = service.mark_done("user_1", job["job_id"], "audio_1")

    assert running["status"] == "running"
    assert running["step"] == "generating_script"
    assert running["progress"] == 40
    assert done["status"] == "done"
    assert done["step"] == "completed"
    assert done["progress"] == 100
    assert done["content_id"] == "audio_1"


def test_job_failed_transition(tmp_path) -> None:
    metadata = JsonMetadataRepository(tmp_path / "metadata")
    service = JobService(metadata)
    job = service.create_job(
        user_id="user_1",
        file_id="file_1",
        filename="note.txt",
        content_type="text/plain",
        file_size=12,
        extracted_text_chars=12,
        duration_minutes=10,
        script_format="summary",
        detail_level="normal",
        voice_style="friendly",
        speed="normal",
    )

    failed = service.mark_failed("user_1", job["job_id"], "rendering_audio", "TTS failed")

    assert failed["status"] == "failed"
    assert failed["step"] == "rendering_audio"
    assert failed["error"] == "TTS failed"


def test_content_job_processor_completes_job(tmp_path) -> None:
    class FakeScriptService:
        def generate_script(
            self,
            user_id: str,
            file_id: str,
            duration_minutes: int,
            script_format: str,
            detail_level: str,
        ) -> dict:
            assert user_id == "user_1"
            assert file_id == "file_1"
            assert duration_minutes == 10
            assert script_format == "summary"
            assert detail_level == "normal"
            return {"script_id": "script_1", "script": "Generated summary script"}

    class FakeAudioService:
        def generate_audio(
            self,
            user_id: str,
            script_id: str,
            voice_style: str,
            speed: str,
        ) -> dict:
            assert user_id == "user_1"
            assert script_id == "script_1"
            assert voice_style == "friendly"
            assert speed == "normal"
            return {"audio_id": "audio_1", "audio_url": "/static/audio/audio_1.wav"}

    from app.application.content_job_processor import ContentJobProcessor

    metadata = JsonMetadataRepository(tmp_path / "metadata")
    metadata.save_file(
        {
            "file_id": "file_1",
            "user_id": "user_1",
            "filename": "note.txt",
            "content_type": "text/plain",
            "size": 12,
            "storage_uri": "local://uploads/user_1/file_1/original.txt",
            "extracted_text_uri": "local://uploads/user_1/file_1/extracted.txt",
            "extracted_text_chars": 12,
            "created_at": "2026-05-25T00:00:00+00:00",
        }
    )
    job_service = JobService(metadata)
    job = job_service.create_job_for_file(
        user_id="user_1",
        file_id="file_1",
        duration_minutes=10,
        script_format="summary",
        detail_level="normal",
        voice_style="friendly",
        speed="normal",
    )
    processor = ContentJobProcessor(
        job_service=job_service,
        script_service=FakeScriptService(),
        audio_service=FakeAudioService(),
    )

    processor.process("user_1", job["job_id"])

    completed = metadata.get_job(job["job_id"], "user_1")
    assert completed["status"] == "done"
    assert completed["step"] == "completed"
    assert completed["progress"] == 100
    assert completed["content_id"] == "audio_1"
