import json
from datetime import timedelta
from pathlib import Path, PurePath
from typing import Any

from google.api_core.exceptions import GoogleAPIError, NotFound
from google.auth.exceptions import GoogleAuthError
from google.cloud import storage

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.audio.schemas import AudioAsset
from app.shared.users import validate_user_id


class GCSStorageService:
    def __init__(
        self,
        settings: Settings,
        client: storage.Client | None = None,
    ) -> None:
        self.settings = settings
        if not settings.gcs_bucket_name:
            raise AppError(
                "CONFIGURATION_ERROR",
                "GCS bucket name must be configured.",
                status_code=500,
                detail={"storage_backend": "gcs"},
            )
        self.bucket_name = settings.gcs_bucket_name
        try:
            self.client = client or storage.Client()
        except GoogleAuthError as exc:
            raise AppError(
                "STORAGE_AUTHENTICATION_FAILED",
                "Failed to initialize GCS client.",
                status_code=500,
                detail={"reason": exc.__class__.__name__},
            ) from exc
        self.bucket = self.client.bucket(self.bucket_name)

    def save_upload(
        self, user_id: str, file_id: str, filename: str, content: bytes
    ) -> str:
        suffix = Path(PurePath(filename).name).suffix.lower()
        object_name = self._object_name(user_id, "uploads", file_id, f"original{suffix}")
        self._upload_bytes(
            object_name=object_name,
            content=content,
            content_type=self._upload_content_type(suffix),
            error_message="Failed to save uploaded file.",
        )
        return self._gcs_uri(object_name)

    def save_extracted_text(self, user_id: str, file_id: str, text: str) -> str:
        object_name = self._object_name(user_id, "uploads", file_id, "extracted.txt")
        self._upload_text(
            object_name=object_name,
            text=text,
            content_type="text/plain; charset=utf-8",
            error_message="Failed to save extracted text.",
        )
        return self._gcs_uri(object_name)

    def read_extracted_text(self, user_id: str, file_id: str) -> str:
        object_name = self._object_name(user_id, "uploads", file_id, "extracted.txt")
        blob = self.bucket.blob(object_name)
        try:
            return blob.download_as_text(encoding="utf-8")
        except NotFound as exc:
            raise AppError(
                "FILE_NOT_FOUND",
                "Uploaded file text was not found.",
                status_code=404,
                detail={"file_id": file_id},
            ) from exc
        except GoogleAPIError as exc:
            raise AppError(
                "STORAGE_READ_FAILED",
                "Failed to read extracted text.",
                status_code=500,
                detail={"reason": exc.__class__.__name__},
            ) from exc

    def save_script_file(
        self, user_id: str, script_id: str, payload: dict[str, Any]
    ) -> str:
        object_name = self._object_name(user_id, "scripts", f"{script_id}.json")
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        self._upload_text(
            object_name=object_name,
            text=text,
            content_type="application/json; charset=utf-8",
            error_message="Failed to save generated script.",
        )
        return self._gcs_uri(object_name)

    def save_audio(
        self, user_id: str, audio_id: str, asset: AudioAsset
    ) -> tuple[str, str]:
        filename = f"{audio_id}.{asset.format}"
        object_name = self._object_name(user_id, "audio", filename)
        blob = self._upload_bytes(
            object_name=object_name,
            content=asset.content,
            content_type=asset.media_type,
            error_message="Failed to save generated audio.",
        )
        storage_uri = self._gcs_uri(object_name)
        return storage_uri, self._signed_read_url(blob)

    def resolve_audio_url(self, storage_uri: str, fallback_url: str) -> str:
        object_name = self._object_name_from_gcs_uri(storage_uri)
        return self._signed_read_url(self.bucket.blob(object_name))

    def _upload_text(
        self,
        object_name: str,
        text: str,
        content_type: str,
        error_message: str,
    ) -> storage.Blob:
        blob = self.bucket.blob(object_name)
        try:
            blob.upload_from_string(text, content_type=content_type)
        except GoogleAPIError as exc:
            raise AppError(
                "STORAGE_UPLOAD_FAILED",
                error_message,
                status_code=500,
                detail={"reason": exc.__class__.__name__},
            ) from exc
        return blob

    def _upload_bytes(
        self,
        object_name: str,
        content: bytes,
        content_type: str,
        error_message: str,
    ) -> storage.Blob:
        blob = self.bucket.blob(object_name)
        try:
            blob.upload_from_string(content, content_type=content_type)
        except GoogleAPIError as exc:
            raise AppError(
                "STORAGE_UPLOAD_FAILED",
                error_message,
                status_code=500,
                detail={"reason": exc.__class__.__name__},
            ) from exc
        return blob

    def _signed_read_url(self, blob: storage.Blob) -> str:
        try:
            return blob.generate_signed_url(
                version="v4",
                expiration=timedelta(
                    minutes=self.settings.gcs_signed_url_expiration_minutes
                ),
                method="GET",
            )
        except (GoogleAPIError, GoogleAuthError, AttributeError, ValueError) as exc:
            raise AppError(
                "STORAGE_SIGNED_URL_FAILED",
                "Failed to generate signed URL for generated audio.",
                status_code=500,
                detail={"reason": exc.__class__.__name__},
            ) from exc

    def _object_name(self, user_id: str, collection: str, *parts: str) -> str:
        safe_user_id = validate_user_id(user_id)
        return "/".join(
            [collection, safe_user_id, *[part.strip("/") for part in parts]]
        )

    def _upload_content_type(self, suffix: str) -> str:
        return {
            ".txt": "text/plain",
            ".pdf": "application/pdf",
        }.get(suffix, "application/octet-stream")

    def _gcs_uri(self, object_name: str) -> str:
        return f"gs://{self.bucket_name}/{object_name}"

    def _object_name_from_gcs_uri(self, storage_uri: str) -> str:
        prefix = f"gs://{self.bucket_name}/"
        if not storage_uri.startswith(prefix):
            raise AppError(
                "STORAGE_URI_INVALID",
                "Stored audio URI does not match the configured GCS bucket.",
                status_code=500,
                detail={"storage_uri": storage_uri, "bucket": self.bucket_name},
            )
        object_name = storage_uri.removeprefix(prefix)
        if not object_name:
            raise AppError(
                "STORAGE_URI_INVALID",
                "Stored audio URI is missing an object name.",
                status_code=500,
                detail={"storage_uri": storage_uri},
            )
        return object_name
