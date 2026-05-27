import json
from pathlib import Path, PurePath
from typing import Any

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.audio.schemas import AudioAsset
from app.shared.users import validate_user_id


class LocalStorageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_dir = settings.local_storage_path
        self.uploads_dir = self.base_dir / "uploads"
        self.scripts_dir = self.base_dir / "scripts"
        self.audio_dir = self.base_dir / "audio"

    def ensure_directories(self) -> None:
        for path in (self.uploads_dir, self.scripts_dir, self.audio_dir):
            path.mkdir(parents=True, exist_ok=True)

    def save_upload(
        self, user_id: str, file_id: str, filename: str, content: bytes
    ) -> str:
        self.ensure_directories()
        safe_user_id = self._safe_segment(user_id)
        suffix = Path(PurePath(filename).name).suffix.lower()
        upload_dir = self.uploads_dir / safe_user_id / file_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / f"original{suffix}"
        try:
            path.write_bytes(content)
        except OSError as exc:
            raise AppError(
                "STORAGE_UPLOAD_FAILED",
                "Failed to save uploaded file.",
                status_code=500,
                detail={"reason": exc.__class__.__name__},
            ) from exc
        return self._local_uri("uploads", safe_user_id, file_id, path.name)

    def save_extracted_text(self, user_id: str, file_id: str, text: str) -> str:
        self.ensure_directories()
        safe_user_id = self._safe_segment(user_id)
        upload_dir = self.uploads_dir / safe_user_id / file_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / "extracted.txt"
        try:
            path.write_text(text, encoding="utf-8")
        except OSError as exc:
            raise AppError(
                "STORAGE_UPLOAD_FAILED",
                "Failed to save extracted text.",
                status_code=500,
                detail={"reason": exc.__class__.__name__},
            ) from exc
        return self._local_uri("uploads", safe_user_id, file_id, path.name)

    def read_extracted_text(self, user_id: str, file_id: str) -> str:
        safe_user_id = self._safe_segment(user_id)
        path = self.uploads_dir / safe_user_id / file_id / "extracted.txt"
        if not path.exists():
            raise AppError(
                "FILE_NOT_FOUND",
                "Uploaded file text was not found.",
                status_code=404,
                detail={"file_id": file_id},
            )
        return path.read_text(encoding="utf-8")

    def save_script_file(
        self, user_id: str, script_id: str, payload: dict[str, Any]
    ) -> str:
        self.ensure_directories()
        safe_user_id = self._safe_segment(user_id)
        user_scripts_dir = self.scripts_dir / safe_user_id
        user_scripts_dir.mkdir(parents=True, exist_ok=True)
        path = user_scripts_dir / f"{script_id}.json"
        try:
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise AppError(
                "STORAGE_UPLOAD_FAILED",
                "Failed to save generated script.",
                status_code=500,
                detail={"reason": exc.__class__.__name__},
            ) from exc
        return self._local_uri("scripts", safe_user_id, path.name)

    def save_audio(
        self, user_id: str, audio_id: str, asset: AudioAsset
    ) -> tuple[str, str]:
        self.ensure_directories()
        safe_user_id = self._safe_segment(user_id)
        user_audio_dir = self.audio_dir / safe_user_id
        user_audio_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{audio_id}.{asset.format}"
        path = user_audio_dir / filename
        try:
            path.write_bytes(asset.content)
        except OSError as exc:
            raise AppError(
                "STORAGE_UPLOAD_FAILED",
                "Failed to save generated audio.",
                status_code=500,
                detail={"reason": exc.__class__.__name__},
            ) from exc
        storage_uri = self._local_uri("audio", safe_user_id, filename)
        relative_url = f"/static/audio/{safe_user_id}/{filename}"
        base_url = self.settings.public_base_url.rstrip("/")
        return storage_uri, f"{base_url}{relative_url}" if base_url else relative_url

    def resolve_audio_url(self, storage_uri: str, fallback_url: str) -> str:
        return fallback_url

    def _safe_segment(self, value: str) -> str:
        return validate_user_id(value)

    def _local_uri(self, *parts: str) -> str:
        return "local://" + "/".join(parts)
