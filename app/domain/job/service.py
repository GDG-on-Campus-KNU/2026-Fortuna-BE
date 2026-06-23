from app.core.errors import AppError
from app.domain.audio.schemas import SpeechSpeed, VoiceStyle
from app.domain.podcast.schemas import DetailLevel, DurationMinutes, ScriptFormat
from app.domain.job.repository import JobRepository
from app.domain.records import JobInput, JobRecord
from app.shared.ids import new_id
from app.shared.time import utc_now_iso


class JobService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    def create_job_for_file(
        self,
        user_id: str,
        file_id: str,
        notebook_id: str,
        duration_minutes: DurationMinutes,
        script_format: ScriptFormat,
        detail_level: DetailLevel,
        voice_style: VoiceStyle,
        speed: SpeechSpeed,
    ) -> dict:
        file_record = self.repository.get_file(file_id, user_id)
        if file_record is None:
            raise AppError(
                "FILE_NOT_FOUND",
                "Uploaded file was not found.",
                status_code=404,
                detail={"file_id": file_id},
            )
        return self.create_job(
            user_id=user_id,
            file_id=file_id,
            notebook_id=notebook_id,
            filename=file_record["filename"],
            content_type=file_record["content_type"],
            file_size=file_record["size"],
            extracted_text_chars=file_record["extracted_text_chars"],
            duration_minutes=duration_minutes,
            script_format=script_format,
            detail_level=detail_level,
            voice_style=voice_style,
            speed=speed,
        )

    def create_job(
        self,
        user_id: str,
        file_id: str,
        notebook_id: str,
        filename: str,
        content_type: str,
        file_size: int,
        extracted_text_chars: int,
        duration_minutes: DurationMinutes,
        script_format: ScriptFormat,
        detail_level: DetailLevel,
        voice_style: VoiceStyle,
        speed: SpeechSpeed,
    ) -> dict:
        now = utc_now_iso()
        record = JobRecord(
            job_id=new_id("job"),
            user_id=user_id,
            notebook_id=notebook_id,
            status="pending",
            step="queued",
            progress=0,
            content_id=None,
            error=None,
            input=JobInput(
                file_id=file_id,
                filename=filename,
                content_type=content_type,
                file_size=file_size,
                extracted_text_chars=extracted_text_chars,
                duration_minutes=duration_minutes,
                format=script_format,
                detail_level=detail_level,
                voice_style=voice_style,
                speed=speed,
            ),
            created_at=now,
            updated_at=now,
        )
        return self.repository.save_job(record.model_dump())

    def get_job(self, user_id: str, job_id: str) -> dict:
        job = self.repository.get_job(job_id, user_id)
        if job is None:
            raise AppError(
                "JOB_NOT_FOUND",
                "Job was not found.",
                status_code=404,
                detail={"job_id": job_id},
            )
        return job

    def mark_running(self, user_id: str, job_id: str, step: str, progress: int) -> dict:
        return self._update_job(
            user_id=user_id,
            job_id=job_id,
            changes={
                "status": "running",
                "step": step,
                "progress": progress,
                "error": None,
                "updated_at": utc_now_iso(),
            },
        )

    def mark_done(self, user_id: str, job_id: str, content_id: str) -> dict:
        return self._update_job(
            user_id=user_id,
            job_id=job_id,
            changes={
                "status": "done",
                "step": "completed",
                "progress": 100,
                "content_id": content_id,
                "error": None,
                "updated_at": utc_now_iso(),
            },
        )

    def mark_failed(self, user_id: str, job_id: str, step: str, error: str) -> dict:
        return self._update_job(
            user_id=user_id,
            job_id=job_id,
            changes={
                "status": "failed",
                "step": step,
                "error": error,
                "updated_at": utc_now_iso(),
            },
        )

    def _update_job(self, user_id: str, job_id: str, changes: dict) -> dict:
        job = self.repository.update_job(job_id, user_id, changes)
        if job is None:
            raise AppError(
                "JOB_NOT_FOUND",
                "Job was not found.",
                status_code=404,
                detail={"job_id": job_id},
            )
        return job
