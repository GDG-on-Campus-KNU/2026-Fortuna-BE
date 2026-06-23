from fastapi.testclient import TestClient
from app.core.config import Settings
from app.core.deps import (
    get_current_user_id,
    get_notebook_service,
    get_source_service,
    get_podcast_service,
)
from app.domain.notebook.service import NotebookService
from app.domain.source.service import SourceService
from app.domain.podcast.service import PodcastService
from app.infra.pdf.extractor import PDFExtractor
from app.infra.repositories.json_repo import JsonMetadataRepository
from app.infra.storage.local import LocalStorageService
from main import app


def test_notebook_operations(tmp_path) -> None:
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
    notebook_service = NotebookService(metadata)
    podcast_service = PodcastService(metadata)

    app.dependency_overrides[get_current_user_id] = lambda: "test-user-id"
    app.dependency_overrides[get_notebook_service] = lambda: notebook_service
    app.dependency_overrides[get_source_service] = lambda: source_service
    app.dependency_overrides[get_podcast_service] = lambda: podcast_service
    client = TestClient(app)

    try:
        # 1. Create a notebook
        response = client.post(
            "/api/v1/notebooks",
            json={"title": "Algorithms & Data Structures"},
        )
        assert response.status_code == 201
        notebook = response.json()
        assert notebook["title"] == "Algorithms & Data Structures"
        assert len(notebook["sources"]) == 0
        assert len(notebook["podcasts"]) == 0
        notebook_id = notebook["id"]

        # 2. Get the notebook details
        detail_response = client.get(f"/api/v1/notebooks/{notebook_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["title"] == "Algorithms & Data Structures"

        # 3. List notebooks
        list_response = client.get("/api/v1/notebooks")
        assert list_response.status_code == 200
        notebooks_list = list_response.json()
        assert len(notebooks_list) == 1
        assert notebooks_list[0]["id"] == notebook_id

        # 4. Upload source file to the notebook
        upload_response = client.post(
            f"/api/v1/notebooks/{notebook_id}/sources",
            files={"file": ("tree.txt", b"Binary tree details.", "text/plain")},
        )
        assert upload_response.status_code == 201
        source = upload_response.json()
        assert source["name"] == "tree.txt"
        assert source["type"] == "txt"
        source_id = source["id"]

        # Check notebook detail again to verify source is present
        detail_response = client.get(f"/api/v1/notebooks/{notebook_id}")
        assert detail_response.status_code == 200
        notebook_detail = detail_response.json()
        assert len(notebook_detail["sources"]) == 1
        assert notebook_detail["sources"][0]["id"] == source_id
        assert notebook_detail["sources"][0]["name"] == "tree.txt"

        # 4b. Add a mock podcast and link to notebook explicitly
        metadata.save_script(
            {
                "script_id": "script_1",
                "user_id": "test-user-id",
                "file_id": source_id,
                "script": "Generated tree script",
                "metadata": {"title": "Tree Structure Summary"},
            }
        )
        metadata.save_audio(
            {
                "audio_id": "audio_1",
                "user_id": "test-user-id",
                "script_id": "script_1",
                "audio_url": "/static/audio/audio_1.wav",
                "voice_style": "friendly",
                "speed": "normal",
                "created_at": "2026-06-06T00:00:00+00:00",
            }
        )
        notebook_service.add_podcast("test-user-id", notebook_id, "audio_1")

        # Get details again to verify podcast is present
        detail_response = client.get(f"/api/v1/notebooks/{notebook_id}")
        assert detail_response.status_code == 200
        notebook_detail = detail_response.json()
        assert len(notebook_detail["podcasts"]) == 1
        assert notebook_detail["podcasts"][0]["id"] == "audio_1"
        assert notebook_detail["podcasts"][0]["title"] == "Tree Structure Summary"

        # 5. Remove source from notebook
        remove_source_res = client.delete(
            f"/api/v1/notebooks/{notebook_id}/sources/{source_id}"
        )
        assert remove_source_res.status_code == 204

        # Verify source is removed in details
        detail_response = client.get(f"/api/v1/notebooks/{notebook_id}")
        assert len(detail_response.json()["sources"]) == 0

        # 6. Delete notebook
        delete_notebook_res = client.delete(f"/api/v1/notebooks/{notebook_id}")
        assert delete_notebook_res.status_code == 204

        # Verify notebook is gone
        list_response = client.get("/api/v1/notebooks")
        assert len(list_response.json()) == 0
    finally:
        app.dependency_overrides.clear()
