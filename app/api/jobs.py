from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.application.podcast_job_processor import PodcastJobProcessor
from app.core.deps import get_podcast_job_processor, get_current_user_id, get_job_service
from app.domain.job.schemas import JobCreateRequest, JobResponse
from app.domain.job.service import JobService


router = APIRouter(tags=["jobs"])


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_job(
    request: JobCreateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    job_service: JobService = Depends(get_job_service),
    processor: PodcastJobProcessor = Depends(get_podcast_job_processor),
) -> JobResponse:
    record = job_service.create_job_for_file(
        user_id=user_id,
        file_id=request.file_id,
        notebook_id=request.notebook_id,
        duration_minutes=request.duration_minutes,
        script_format=request.format,
        detail_level=request.detail_level,
        voice_style=request.voice_style,
        speed=request.speed,
    )
    background_tasks.add_task(processor.process, user_id, record["job_id"])
    return JobResponse(**record)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    return JobResponse(**job_service.get_job(user_id, job_id))
