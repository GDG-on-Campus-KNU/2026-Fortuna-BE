from pydantic import BaseModel


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    content_type: str
    size: int
    extracted_text_chars: int

