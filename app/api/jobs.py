from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core.config import Settings, get_settings
from app.core.deps import get_current_user_id, get_job_service, get_source_service
from app.core.errors import AppError
from app.domain.audio.schemas import SpeechSpeed, VoiceStyle
from app.domain.content.schemas import DetailLevel, ScriptFormat
from app.domain.job.schemas import JobResponse
from app.domain.job.service import JobService
from app.domain.source.service import SourceService


router = APIRouter(tags=["jobs"])


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_job(
    file: UploadFile = File(...),
    duration_minutes: int = Form(10),
    podcast_format: ScriptFormat = Form("dialogue", alias="format"),
    detail_level: DetailLevel = Form("normal"),
    voice_style: VoiceStyle = Form("friendly"),
    speed: SpeechSpeed = Form("normal"),
    user_id: str = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
    source_service: SourceService = Depends(get_source_service),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    if duration_minutes not in (5, 10, 20):
        raise AppError(
            "INVALID_OPTION",
            "Request validation failed.",
            status_code=422,
            detail={"duration_minutes": duration_minutes},
        )

    content = await file.read(settings.max_upload_bytes + 1)
    file_record = source_service.upload_and_extract(
        user_id=user_id,
        filename=file.filename,
        content_type=file.content_type,
        content=content,
    )
    record = job_service.create_job(
        user_id=user_id,
        file_id=file_record["file_id"],
        filename=file_record["filename"],
        content_type=file_record["content_type"],
        file_size=file_record["size"],
        extracted_text_chars=file_record["extracted_text_chars"],
        duration_minutes=duration_minutes,  # type: ignore[arg-type]
        script_format=podcast_format,
        detail_level=detail_level,
        voice_style=voice_style,
        speed=speed,
    )
    return JobResponse(**record)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    return JobResponse(**job_service.get_job(user_id, job_id))

