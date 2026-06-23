from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.deps import get_current_user_id, get_source_service, get_notebook_service
from app.domain.source.service import SourceService
from app.domain.notebook.service import NotebookService
from app.infra.pdf.extractor import PDFExtractor
from app.infra.repositories.json_repo import JsonMetadataRepository
from app.infra.storage.local import LocalStorageService
from main import app


def build_source_service(tmp_path: Path, max_upload_mb: int = 20) -> SourceService:
    settings = Settings(
        app_env="test",
        local_storage_dir=str(tmp_path / "storage"),
        metadata_dir=str(tmp_path / "storage" / "metadata"),
        max_upload_mb=max_upload_mb,
    )
    storage = LocalStorageService(settings)
    metadata = JsonMetadataRepository(settings.metadata_path)
    return SourceService(settings, storage, metadata, PDFExtractor())


def test_txt_upload_extracts_text(tmp_path: Path) -> None:
    metadata = JsonMetadataRepository(tmp_path / "metadata")
    notebook_service = NotebookService(metadata)
    app.dependency_overrides[get_current_user_id] = lambda: "test-user-id"
    app.dependency_overrides[get_source_service] = lambda: build_source_service(tmp_path)
    app.dependency_overrides[get_notebook_service] = lambda: notebook_service
    client = TestClient(app)

    try:
        # Create a notebook
        nb_res = client.post(
            "/api/v1/notebooks",
            json={"title": "Test Notebook"},
        )
        assert nb_res.status_code == 201
        notebook_id = nb_res.json()["id"]

        response = client.post(
            f"/api/v1/notebooks/{notebook_id}/sources",
            files={"file": ("note.txt", "테스트 자료입니다.".encode("utf-8"), "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "note.txt"
    assert body["type"] == "txt"
    assert "id" in body


def test_invalid_file_type_returns_error(tmp_path: Path) -> None:
    metadata = JsonMetadataRepository(tmp_path / "metadata")
    notebook_service = NotebookService(metadata)
    app.dependency_overrides[get_current_user_id] = lambda: "test-user-id"
    app.dependency_overrides[get_source_service] = lambda: build_source_service(tmp_path)
    app.dependency_overrides[get_notebook_service] = lambda: notebook_service
    client = TestClient(app)

    try:
        # Create a notebook
        nb_res = client.post(
            "/api/v1/notebooks",
            json={"title": "Test Notebook"},
        )
        assert nb_res.status_code == 201
        notebook_id = nb_res.json()["id"]

        response = client.post(
            f"/api/v1/notebooks/{notebook_id}/sources",
            files={"file": ("image.png", b"png", "image/png")},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_file_too_large_returns_error(tmp_path: Path) -> None:
    metadata = JsonMetadataRepository(tmp_path / "metadata")
    notebook_service = NotebookService(metadata)
    app.dependency_overrides[get_current_user_id] = lambda: "test-user-id"
    app.dependency_overrides[get_source_service] = lambda: build_source_service(
        tmp_path,
        max_upload_mb=0,
    )
    app.dependency_overrides[get_notebook_service] = lambda: notebook_service
    client = TestClient(app)

    try:
        # Create a notebook
        nb_res = client.post(
            "/api/v1/notebooks",
            json={"title": "Test Notebook"},
        )
        assert nb_res.status_code == 201
        notebook_id = nb_res.json()["id"]

        response = client.post(
            f"/api/v1/notebooks/{notebook_id}/sources",
            files={"file": ("note.txt", b"x", "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_pdf_extraction_failure_returns_app_error() -> None:
    with pytest.raises(Exception) as exc_info:
        PDFExtractor().extract_text(b"not a pdf")

    assert getattr(exc_info.value, "code") == "PDF_EXTRACTION_FAILED"
