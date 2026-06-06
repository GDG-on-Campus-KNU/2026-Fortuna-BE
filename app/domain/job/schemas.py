from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.audio.schemas import SpeechSpeed, VoiceStyle
from app.domain.podcast.schemas import DetailLevel, DurationMinutes, ScriptFormat


JobStatus = Literal["pending", "running", "done", "failed"]


class JobCreateRequest(BaseModel):
    file_id: str
    notebook_id: str
    duration_minutes: DurationMinutes = 10
    format: ScriptFormat = "summary"
    detail_level: DetailLevel = "normal"
    voice_style: VoiceStyle = "friendly"
    speed: SpeechSpeed = "normal"


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    step: str
    progress: int = Field(ge=0, le=100)
    content_id: str | None = None
    error: str | None = None
    input: dict[str, Any]
    created_at: str
    updated_at: str
