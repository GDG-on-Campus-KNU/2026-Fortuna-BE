from app.core.errors import AppError
from app.domain.content.repository import AudioUrlResolver, ContentRepository


class ContentService:
    def __init__(
        self,
        repository: ContentRepository,
        audio_url_resolver: AudioUrlResolver | None = None,
    ) -> None:
        self.repository = repository
        self.audio_url_resolver = audio_url_resolver

    def list_contents(self, user_id: str) -> list[dict]:
        contents = [
            content
            for audio_record in self.repository.list_audio(user_id)
            if (content := self._build_content(user_id, audio_record)) is not None
        ]
        return sorted(contents, key=lambda item: item["created_at"], reverse=True)

    def get_content(self, user_id: str, content_id: str) -> dict:
        audio_record = self.repository.get_audio(content_id, user_id)
        if not audio_record:
            raise AppError(
                "CONTENT_NOT_FOUND",
                "Content was not found.",
                status_code=404,
                detail={"content_id": content_id},
            )

        content = self._build_content(user_id, audio_record, strict=True)
        if content is None:
            raise AppError(
                "CONTENT_NOT_FOUND",
                "Content metadata is incomplete.",
                status_code=404,
                detail={"content_id": content_id},
            )
        return content

    def _build_content(
        self, user_id: str, audio_record: dict, strict: bool = False
    ) -> dict | None:
        script_id = audio_record.get("script_id")
        if not script_id:
            return self._missing(strict)

        script_record = self.repository.get_script(script_id, user_id)
        if not script_record:
            return self._missing(strict)

        file_id = script_record.get("file_id")
        if not file_id:
            return self._missing(strict)

        file_record = self.repository.get_file(file_id, user_id)
        if not file_record:
            return self._missing(strict)

        audio_id = audio_record["audio_id"]
        audio_url = audio_record.get("audio_url", "")
        storage_uri = audio_record.get("storage_uri")
        if self.audio_url_resolver is not None and storage_uri:
            audio_url = self.audio_url_resolver.resolve_audio_url(
                storage_uri=storage_uri,
                fallback_url=audio_url,
            )

        return {
            "content_id": audio_id,
            "script_id": script_id,
            "file_id": file_id,
            "filename": file_record.get("filename", ""),
            "script": script_record.get("script", ""),
            "audio_url": audio_url,
            "created_at": audio_record.get("created_at")
            or script_record.get("created_at")
            or file_record.get("created_at")
            or "",
            "metadata": {
                "script": script_record.get("metadata", {}),
                "tts": {
                    "voice_style": audio_record.get("voice_style"),
                    "speed": audio_record.get("speed"),
                },
            },
        }

    def _missing(self, strict: bool) -> None:
        if strict:
            raise AppError(
                "CONTENT_NOT_FOUND",
                "Content metadata is incomplete.",
                status_code=404,
            )
        return None
