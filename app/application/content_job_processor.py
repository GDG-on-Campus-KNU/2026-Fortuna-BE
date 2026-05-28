from app.application.generate_content import (
    AudioGenerationService,
    ScriptGenerationService,
)
from app.core.errors import AppError
from app.domain.job.service import JobService


class ContentJobProcessor:
    def __init__(
        self,
        job_service: JobService,
        script_service: ScriptGenerationService,
        audio_service: AudioGenerationService,
    ) -> None:
        self.job_service = job_service
        self.script_service = script_service
        self.audio_service = audio_service

    def process(self, user_id: str, job_id: str) -> None:
        step = "queued"
        try:
            job = self.job_service.get_job(user_id, job_id)
            job_input = job["input"]

            step = "generating_script"
            self.job_service.mark_running(user_id, job_id, step, 20)
            script = self.script_service.generate_script(
                user_id=user_id,
                file_id=job_input["file_id"],
                duration_minutes=job_input["duration_minutes"],
                script_format=job_input["format"],
                detail_level=job_input["detail_level"],
            )

            step = "rendering_audio"
            self.job_service.mark_running(user_id, job_id, step, 70)
            audio = self.audio_service.generate_audio(
                user_id=user_id,
                script_id=script["script_id"],
                voice_style=job_input["voice_style"],
                speed=job_input["speed"],
            )

            self.job_service.mark_done(user_id, job_id, audio["audio_id"])
        except AppError as exc:
            self._mark_failed_safely(
                user_id,
                job_id,
                step,
                f"{exc.code}: {exc.message}",
            )
        except Exception as exc:
            self._mark_failed_safely(
                user_id,
                job_id,
                step,
                f"{exc.__class__.__name__}: {exc}",
            )

    def _mark_failed_safely(
        self,
        user_id: str,
        job_id: str,
        step: str,
        error: str,
    ) -> None:
        try:
            self.job_service.mark_failed(user_id, job_id, step, error)
        except AppError:
            return
