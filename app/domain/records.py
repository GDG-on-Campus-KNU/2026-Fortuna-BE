from typing import Any

from pydantic import BaseModel, Field

from app.domain.audio.schemas import SpeechSpeed, VoiceStyle
from app.domain.podcast.schemas import DetailLevel, DurationMinutes, ScriptFormat
from app.domain.job.schemas import JobStatus


class FileRecord(BaseModel):
    file_id: str
    user_id: str
    filename: str
    content_type: str
    size: int
    storage_uri: str
    extracted_text_uri: str
    extracted_text_chars: int
    created_at: str


class ScriptRecord(BaseModel):
    script_id: str
    user_id: str
    file_id: str
    script: str
    metadata: dict[str, Any]
    prompt_chars: int
    storage_uri: str
    created_at: str


class AudioRecord(BaseModel):
    audio_id: str
    user_id: str
    script_id: str
    audio_url: str
    audio_format: str
    media_type: str
    voice_style: VoiceStyle
    speed: SpeechSpeed
    metadata: dict[str, Any]
    storage_uri: str
    created_at: str


class JobInput(BaseModel):
    file_id: str
    filename: str
    content_type: str
    file_size: int
    extracted_text_chars: int
    duration_minutes: DurationMinutes
    format: ScriptFormat
    detail_level: DetailLevel
    voice_style: VoiceStyle
    speed: SpeechSpeed


class JobRecord(BaseModel):
    job_id: str
    user_id: str
    notebook_id: str | None = None
    status: JobStatus
    step: str
    progress: int = Field(ge=0, le=100)
    content_id: str | None = None
    error: str | None = None
    input: JobInput
    created_at: str
    updated_at: str

