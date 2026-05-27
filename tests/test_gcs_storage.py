from datetime import timedelta
import json

import pytest
from google.api_core.exceptions import NotFound
from google.auth.exceptions import DefaultCredentialsError

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.audio.schemas import AudioAsset
from app.infra.storage.gcs import GCSStorageService


class FakeBlob:
    def __init__(self, name: str) -> None:
        self.name = name
        self.content: bytes | None = None
        self.content_type: str | None = None
        self.signed_url_kwargs: dict | None = None

    def upload_from_string(self, data: bytes | str, content_type: str) -> None:
        self.content = data.encode("utf-8") if isinstance(data, str) else data
        self.content_type = content_type

    def download_as_text(self, encoding: str) -> str:
        if self.content is None:
            raise NotFound("missing")
        return self.content.decode(encoding)

    def generate_signed_url(self, **kwargs) -> str:
        self.signed_url_kwargs = kwargs
        return f"https://storage.example/{self.name}?X-Goog-Signature=fake"


class FakeBucket:
    def __init__(self) -> None:
        self.blobs: dict[str, FakeBlob] = {}

    def blob(self, name: str) -> FakeBlob:
        if name not in self.blobs:
            self.blobs[name] = FakeBlob(name)
        return self.blobs[name]


class FakeClient:
    def __init__(self, bucket: FakeBucket) -> None:
        self.fake_bucket = bucket
        self.bucket_name: str | None = None

    def bucket(self, name: str) -> FakeBucket:
        self.bucket_name = name
        return self.fake_bucket


def build_storage() -> tuple[GCSStorageService, FakeBucket, FakeClient]:
    bucket = FakeBucket()
    client = FakeClient(bucket)
    settings = Settings(
        gcs_bucket_name="fortuna-test-bucket",
        gcs_signed_url_expiration_minutes=15,
        _env_file=None,
    )
    return GCSStorageService(settings, client=client), bucket, client


def test_gcs_storage_saves_upload_text_script_and_signed_audio_url() -> None:
    storage, bucket, client = build_storage()

    upload_uri = storage.save_upload("user_1", "file_1", "note.txt", b"source")
    text_uri = storage.save_extracted_text("user_1", "file_1", "extracted")
    script_uri = storage.save_script_file(
        "user_1",
        "script_1",
        {"script": "hello", "metadata": {"duration_minutes": 10}},
    )
    audio_uri, audio_url = storage.save_audio(
        "user_1",
        "audio_1",
        AudioAsset(content=b"audio", format="wav", media_type="audio/wav"),
    )
    refreshed_audio_url = storage.resolve_audio_url(audio_uri, audio_url)

    assert client.bucket_name == "fortuna-test-bucket"
    assert upload_uri == "gs://fortuna-test-bucket/uploads/user_1/file_1/original.txt"
    assert text_uri == "gs://fortuna-test-bucket/uploads/user_1/file_1/extracted.txt"
    assert script_uri == "gs://fortuna-test-bucket/scripts/user_1/script_1.json"
    assert audio_uri == "gs://fortuna-test-bucket/audio/user_1/audio_1.wav"
    assert audio_url.startswith("https://storage.example/audio/user_1/audio_1.wav?")
    assert refreshed_audio_url.startswith(
        "https://storage.example/audio/user_1/audio_1.wav?"
    )

    assert bucket.blobs["uploads/user_1/file_1/original.txt"].content == b"source"
    assert (
        bucket.blobs["uploads/user_1/file_1/original.txt"].content_type
        == "text/plain"
    )
    assert storage.read_extracted_text("user_1", "file_1") == "extracted"

    script_blob = bucket.blobs["scripts/user_1/script_1.json"]
    assert script_blob.content_type == "application/json; charset=utf-8"
    assert json.loads(script_blob.content.decode("utf-8"))["script"] == "hello"

    audio_blob = bucket.blobs["audio/user_1/audio_1.wav"]
    assert audio_blob.content == b"audio"
    assert audio_blob.content_type == "audio/wav"
    assert audio_blob.signed_url_kwargs == {
        "version": "v4",
        "expiration": timedelta(minutes=15),
        "method": "GET",
    }


def test_gcs_storage_requires_bucket_name() -> None:
    settings = Settings(gcs_bucket_name=None, _env_file=None)

    with pytest.raises(AppError) as exc_info:
        GCSStorageService(settings, client=FakeClient(FakeBucket()))

    assert exc_info.value.code == "CONFIGURATION_ERROR"


def test_gcs_storage_maps_default_credential_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_default_credentials_error() -> None:
        raise DefaultCredentialsError("missing")

    monkeypatch.setattr(
        "app.infra.storage.gcs.storage.Client",
        raise_default_credentials_error,
    )
    settings = Settings(gcs_bucket_name="fortuna-test-bucket", _env_file=None)

    with pytest.raises(AppError) as exc_info:
        GCSStorageService(settings)

    assert exc_info.value.code == "STORAGE_AUTHENTICATION_FAILED"


def test_gcs_read_extracted_text_maps_missing_blob_to_file_not_found() -> None:
    storage, _, _ = build_storage()

    with pytest.raises(AppError) as exc_info:
        storage.read_extracted_text("user_1", "file_missing")

    assert exc_info.value.code == "FILE_NOT_FOUND"
    assert exc_info.value.status_code == 404


def test_gcs_resolve_audio_url_rejects_other_bucket_uri() -> None:
    storage, _, _ = build_storage()

    with pytest.raises(AppError) as exc_info:
        storage.resolve_audio_url("gs://other-bucket/audio/user_1/audio_1.wav", "")

    assert exc_info.value.code == "STORAGE_URI_INVALID"
