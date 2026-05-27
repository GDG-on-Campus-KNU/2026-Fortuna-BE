from pathlib import Path, PurePath

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.records import FileRecord
from app.domain.source.repository import SourceRepository, SourceStorage, TextExtractor
from app.shared.ids import new_id
from app.shared.time import utc_now_iso


class SourceService:
    def __init__(
        self,
        settings: Settings,
        storage: SourceStorage,
        repository: SourceRepository,
        text_extractor: TextExtractor,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.repository = repository
        self.text_extractor = text_extractor

    def upload_and_extract(
        self,
        user_id: str,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> dict:
        clean_filename = self._clean_filename(filename)
        suffix = Path(clean_filename).suffix.lower()
        self._validate_extension(suffix)

        size = len(content)
        if size > self.settings.max_upload_bytes:
            raise AppError(
                "FILE_TOO_LARGE",
                f"File size must be {self.settings.max_upload_mb}MB or less.",
                status_code=413,
                detail={"max_upload_mb": self.settings.max_upload_mb},
            )

        canonical_content_type = self._canonical_content_type(suffix, content_type)
        extracted_text = self._extract_text(suffix, content)

        file_id = new_id("file")
        storage_uri = self.storage.save_upload(user_id, file_id, clean_filename, content)
        extracted_text_uri = self.storage.save_extracted_text(
            user_id, file_id, extracted_text
        )

        record = FileRecord(
            file_id=file_id,
            user_id=user_id,
            filename=clean_filename,
            content_type=canonical_content_type,
            size=size,
            storage_uri=storage_uri,
            extracted_text_uri=extracted_text_uri,
            extracted_text_chars=len(extracted_text),
            created_at=utc_now_iso(),
        )
        return self.repository.save_file(record.model_dump())

    def _clean_filename(self, filename: str | None) -> str:
        if not filename:
            raise AppError(
                "INVALID_FILE_TYPE",
                "Uploaded file must have a filename.",
                status_code=400,
            )
        return PurePath(filename).name

    def _validate_extension(self, suffix: str) -> None:
        if suffix not in frozenset({".txt", ".pdf"}):
            raise AppError(
                "INVALID_FILE_TYPE",
                "Only txt and pdf files are supported.",
                status_code=400,
                detail={"allowed_extensions": [".txt", ".pdf"]},
            )

    def _canonical_content_type(self, suffix: str, content_type: str | None) -> str:
        allowed = {
            ".txt": {"text/plain", "application/octet-stream"},
            ".pdf": {"application/pdf", "application/octet-stream"},
        }
        canonical = {".txt": "text/plain", ".pdf": "application/pdf"}
        normalized_content_type = (
            content_type.split(";")[0].strip().lower() if content_type else None
        )
        if normalized_content_type and normalized_content_type not in allowed[suffix]:
            raise AppError(
                "INVALID_FILE_TYPE",
                "Only txt and pdf files are supported.",
                status_code=400,
                detail={"content_type": normalized_content_type},
            )
        return canonical[suffix]

    def _extract_text(self, suffix: str, content: bytes) -> str:
        if suffix == ".pdf":
            return self.text_extractor.extract_text(content)

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = content.decode("cp949")
            except UnicodeDecodeError as exc:
                raise AppError(
                    "INVALID_FILE_TYPE",
                    "Text file must be encoded as UTF-8 or CP949.",
                    status_code=422,
                ) from exc

        text = text.strip()
        if not text:
            raise AppError(
                "INVALID_FILE_TYPE",
                "Uploaded text file is empty.",
                status_code=422,
            )
        return text

