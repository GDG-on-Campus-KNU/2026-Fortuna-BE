from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from app.application.content_job_processor import ContentJobProcessor
from app.application.generate_content import AudioGenerationService, ScriptGenerationService
from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.errors import AppError
from app.domain.audio.renderer import AudioRenderer
from app.domain.content.prompt_builder import PromptBuilder
from app.domain.content.service import ContentService
from app.domain.job.service import JobService
from app.domain.source.service import SourceService
from app.infra.llm.gemini import GeminiService
from app.infra.mixer.passthrough import PassthroughAudioMixer
from app.infra.music.null import NullMusicGenerator
from app.infra.pdf.extractor import PDFExtractor
from app.infra.repositories.json_repo import JsonMetadataRepository
from app.infra.repositories.postgres import PostgresMetadataRepository
from app.infra.speech.gemini import GeminiSpeechSynthesizer
from app.infra.speech.google import GoogleCloudSpeechSynthesizer
from app.infra.storage.gcs import GCSStorageService
from app.infra.storage.local import LocalStorageService
from app.models.user import User


@lru_cache
def get_storage_service() -> LocalStorageService | GCSStorageService:
    settings = get_settings()
    if settings.storage_backend == "local":
        storage = LocalStorageService(settings)
        storage.ensure_directories()
        return storage
    if settings.storage_backend == "gcs":
        return GCSStorageService(settings)
    raise AppError(
        "CONFIGURATION_ERROR",
        "Unsupported storage backend.",
        status_code=500,
        detail={"storage_backend": settings.storage_backend},
    )


@lru_cache
def get_metadata_repository() -> JsonMetadataRepository | PostgresMetadataRepository:
    settings = get_settings()
    if settings.metadata_backend == "json":
        return JsonMetadataRepository(settings.metadata_path)
    if settings.metadata_backend == "postgres":
        return PostgresMetadataRepository(settings)
    raise AppError(
        "CONFIGURATION_ERROR",
        "Unsupported metadata backend.",
        status_code=500,
        detail={"metadata_backend": settings.metadata_backend},
    )


def get_current_user_id(current_user: User = Depends(get_current_user)) -> str:
    return str(current_user.id)


def get_static_audio_dir() -> Path | None:
    settings = get_settings()
    if settings.storage_backend == "local":
        storage = LocalStorageService(settings)
        storage.ensure_directories()
        return storage.audio_dir
    return None


def get_source_service() -> SourceService:
    settings = get_settings()
    return SourceService(
        settings=settings,
        storage=get_storage_service(),
        repository=get_metadata_repository(),
        text_extractor=PDFExtractor(),
    )


def get_script_service() -> ScriptGenerationService:
    settings = get_settings()
    repository = get_metadata_repository()
    return ScriptGenerationService(
        storage=get_storage_service(),
        source_repository=repository,
        script_repository=repository,
        prompt_builder=PromptBuilder(),
        llm=GeminiService(settings),
    )


def get_audio_service() -> AudioGenerationService:
    settings = get_settings()
    repository = get_metadata_repository()
    if settings.tts_provider == "gemini":
        speech_synthesizer = GeminiSpeechSynthesizer(settings)
    elif settings.tts_provider == "google_cloud":
        speech_synthesizer = GoogleCloudSpeechSynthesizer(settings)
    else:
        raise AppError(
            "CONFIGURATION_ERROR",
            "Unsupported TTS provider.",
            status_code=500,
            detail={"tts_provider": settings.tts_provider},
        )
    renderer = AudioRenderer(
        speech_synthesizer=speech_synthesizer,
        music_generator=NullMusicGenerator(),
        mixer=PassthroughAudioMixer(),
    )
    return AudioGenerationService(
        storage=get_storage_service(),
        script_repository=repository,
        audio_repository=repository,
        renderer=renderer,
        speech_provider=settings.tts_provider,
    )


def get_content_service() -> ContentService:
    return ContentService(
        repository=get_metadata_repository(),
        audio_url_resolver=get_storage_service(),
    )


def get_job_service() -> JobService:
    return JobService(repository=get_metadata_repository())


def get_content_job_processor() -> ContentJobProcessor:
    return ContentJobProcessor(
        job_service=get_job_service(),
        script_service=get_script_service(),
        audio_service=get_audio_service(),
    )


def reset_dependency_caches() -> None:
    get_settings.cache_clear()
    get_storage_service.cache_clear()
    get_metadata_repository.cache_clear()
