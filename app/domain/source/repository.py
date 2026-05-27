from typing import Protocol


class TextExtractor(Protocol):
    def extract_text(self, content: bytes) -> str: ...


class SourceStorage(Protocol):
    def save_upload(
        self, user_id: str, file_id: str, filename: str, content: bytes
    ) -> str: ...

    def save_extracted_text(self, user_id: str, file_id: str, text: str) -> str: ...

    def read_extracted_text(self, user_id: str, file_id: str) -> str: ...


class SourceRepository(Protocol):
    def save_file(self, record: dict) -> dict: ...

    def get_file(self, file_id: str, user_id: str | None = None) -> dict | None: ...

    def list_files(self, user_id: str) -> list[dict]: ...

