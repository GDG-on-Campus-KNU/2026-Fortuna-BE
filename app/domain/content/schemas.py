from typing import Any, Literal

from pydantic import BaseModel


DurationMinutes = Literal[5, 10, 20]
ScriptFormat = Literal["summary"]
DetailLevel = Literal["brief", "normal", "detailed"]


class ScriptOptions(BaseModel):
    duration_minutes: DurationMinutes
    format: ScriptFormat
    detail_level: DetailLevel


class ScriptGenerateRequest(ScriptOptions):
    file_id: str


class ScriptGenerateResponse(BaseModel):
    script_id: str
    script: str
    metadata: ScriptOptions


class ContentListItem(BaseModel):
    content_id: str
    script_id: str
    file_id: str
    filename: str
    audio_url: str
    created_at: str
    metadata: dict[str, Any]


class ContentResponse(ContentListItem):
    script: str
