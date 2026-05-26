from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.deps import get_current_user_id, get_job_service, get_source_service
from app.domain.content.service import ContentService
from app.domain.job.service import JobService
from app.domain.source.service import SourceService
from app.infra.pdf.extractor import PDFExtractor
from app.infra.repositories.json_repo import JsonMetadataRepository
from app.infra.storage.local import LocalStorageService
from main import app


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
    client = TestClient(app)

    try:
        response = client.post(
            "/jobs",
            data={
                "duration_minutes": 10,
                "format": "dialogue",
                "detail_level": "normal",
                "voice_style": "friendly",
                "speed": "normal",
            },
            files={"file": ("note.txt", b"content", "text/plain")},
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
        assert lookup.json()["input"]["file_id"] == created["input"]["file_id"]
        job_record = metadata.get_job(created["job_id"], "test-user-id")
        file_id = job_record["input"]["file_id"]
        assert metadata.get_file(file_id, "test-user-id")["filename"] == "note.txt"
        assert job_record["input"]["content_type"] == "text/plain"
        assert job_record["input"]["extracted_text_chars"] > 0
    finally:
        app.dependency_overrides.clear()


def test_job_rejects_invalid_file_type(tmp_path) -> None:
    metadata = JsonMetadataRepository(tmp_path / "metadata")
    settings = Settings(
        app_env="test",
        local_storage_dir=str(tmp_path / "storage"),
        metadata_dir=str(tmp_path / "metadata"),
        _env_file=None,
    )
    source_service = SourceService(
        settings=settings,
        storage=LocalStorageService(settings),
        repository=metadata,
        text_extractor=PDFExtractor(),
    )
    app.dependency_overrides[get_current_user_id] = lambda: "test-user-id"
    app.dependency_overrides[get_job_service] = lambda: JobService(metadata)
    app.dependency_overrides[get_source_service] = lambda: source_service
    client = TestClient(app)

    try:
        response = client.post(
            "/jobs",
            data={
                "duration_minutes": 10,
                "format": "dialogue",
                "detail_level": "normal",
                "voice_style": "friendly",
                "speed": "normal",
            },
            files={"file": ("image.png", b"png", "image/png")},
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"
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
        script_format="dialogue",
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
        script_format="dialogue",
        detail_level="normal",
        voice_style="friendly",
        speed="normal",
    )

    failed = service.mark_failed("user_1", job["job_id"], "rendering_audio", "TTS failed")

    assert failed["status"] == "failed"
    assert failed["step"] == "rendering_audio"
    assert failed["error"] == "TTS failed"
