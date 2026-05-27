from typing import Any, Literal

from pydantic import BaseModel, Field


JobStatus = Literal["pending", "running", "done", "failed"]


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

