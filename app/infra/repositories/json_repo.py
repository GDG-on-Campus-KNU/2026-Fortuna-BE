import json
import threading
from pathlib import Path
from typing import Any

from app.core.errors import AppError


class JsonMetadataRepository:
    def __init__(self, metadata_dir: Path) -> None:
        self.metadata_dir = metadata_dir
        self._lock = threading.Lock()

    def _path(self, collection: str) -> Path:
        return self.metadata_dir / f"{collection}.json"

    def _load(self, collection: str) -> dict[str, dict[str, Any]]:
        path = self._path(collection)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AppError(
                "METADATA_SAVE_FAILED",
                "Failed to read metadata.",
                status_code=500,
                detail={"collection": collection, "reason": exc.__class__.__name__},
            ) from exc

    def _save(self, collection: str, payload: dict[str, dict[str, Any]]) -> None:
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(collection)
        temp_path = path.with_suffix(".json.tmp")
        try:
            temp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_path.replace(path)
        except OSError as exc:
            raise AppError(
                "METADATA_SAVE_FAILED",
                "Failed to save metadata.",
                status_code=500,
                detail={"collection": collection, "reason": exc.__class__.__name__},
            ) from exc

    def _upsert(self, collection: str, key: str, record: dict[str, Any]) -> dict:
        with self._lock:
            payload = self._load(collection)
            payload[record[key]] = record
            self._save(collection, payload)
        return record

    def _filter_user(self, records: list[dict], user_id: str) -> list[dict]:
        return [record for record in records if record.get("user_id") == user_id]

    def _get_scoped(
        self, collection: str, key: str, user_id: str | None
    ) -> dict | None:
        record = self._load(collection).get(key)
        if record is None:
            return None
        if user_id is not None and record.get("user_id") != user_id:
            return None
        return record

    def save_file(self, record: dict) -> dict:
        return self._upsert("files", "file_id", record)

    def get_file(self, file_id: str, user_id: str | None = None) -> dict | None:
        return self._get_scoped("files", file_id, user_id)

    def list_files(self, user_id: str) -> list[dict]:
        return self._filter_user(list(self._load("files").values()), user_id)

    def save_script(self, record: dict) -> dict:
        return self._upsert("scripts", "script_id", record)

    def get_script(self, script_id: str, user_id: str | None = None) -> dict | None:
        return self._get_scoped("scripts", script_id, user_id)

    def list_scripts(self, user_id: str) -> list[dict]:
        return self._filter_user(list(self._load("scripts").values()), user_id)

    def save_audio(self, record: dict) -> dict:
        return self._upsert("audio", "audio_id", record)

    def get_audio(self, audio_id: str, user_id: str | None = None) -> dict | None:
        return self._get_scoped("audio", audio_id, user_id)

    def list_audio(self, user_id: str) -> list[dict]:
        return self._filter_user(list(self._load("audio").values()), user_id)

    def save_job(self, record: dict) -> dict:
        return self._upsert("jobs", "job_id", record)

    def update_job(
        self, job_id: str, user_id: str | None, changes: dict
    ) -> dict | None:
        with self._lock:
            payload = self._load("jobs")
            record = payload.get(job_id)
            if record is None:
                return None
            if user_id is not None and record.get("user_id") != user_id:
                return None
            record = {**record, **changes}
            payload[job_id] = record
            self._save("jobs", payload)
        return record

    def get_job(self, job_id: str, user_id: str | None = None) -> dict | None:
        return self._get_scoped("jobs", job_id, user_id)

    def list_jobs(self, user_id: str) -> list[dict]:
        return self._filter_user(list(self._load("jobs").values()), user_id)

