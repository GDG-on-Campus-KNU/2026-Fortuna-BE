from app.core.errors import AppError
from app.domain.audio.renderer import AudioRenderer
from app.domain.audio.repository import AudioRepository, AudioStorage
from app.domain.audio.schemas import AudioRenderOptions, SpeechOptions, SpeechSpeed, VoiceStyle
from app.domain.content.prompt_builder import PromptBuilder
from app.domain.content.repository import ContentStorage, LLMClient, ScriptRepository
from app.domain.content.schemas import DetailLevel, DurationMinutes, ScriptFormat
from app.domain.records import AudioRecord, ScriptRecord
from app.domain.source.repository import SourceRepository
from app.shared.ids import new_id
from app.shared.time import utc_now_iso


class ScriptGenerationService:
    def __init__(
        self,
        storage: ContentStorage,
        source_repository: SourceRepository,
        script_repository: ScriptRepository,
        prompt_builder: PromptBuilder,
        llm: LLMClient,
    ) -> None:
        self.storage = storage
        self.source_repository = source_repository
        self.script_repository = script_repository
        self.prompt_builder = prompt_builder
        self.llm = llm

    def generate_script(
        self,
        user_id: str,
        file_id: str,
        duration_minutes: DurationMinutes,
        script_format: ScriptFormat,
        detail_level: DetailLevel,
    ) -> dict:
        file_record = self.source_repository.get_file(file_id, user_id)
        if file_record is None:
            raise AppError(
                "FILE_NOT_FOUND",
                "Uploaded file was not found.",
                status_code=404,
                detail={"file_id": file_id},
            )

        source_text = self.storage.read_extracted_text(user_id, file_id)
        prompt = self.prompt_builder.build(
            source_text=source_text,
            duration_minutes=duration_minutes,
            script_format=script_format,
            detail_level=detail_level,
        )
        script = self.llm.generate_script(prompt)
        script_id = new_id("script")
        options = {
            "duration_minutes": duration_minutes,
            "format": script_format,
            "detail_level": detail_level,
        }
        created_at = utc_now_iso()
        storage_payload = {"script": script, "metadata": options}
        storage_uri = self.storage.save_script_file(user_id, script_id, storage_payload)
        record = ScriptRecord(
            script_id=script_id,
            user_id=user_id,
            file_id=file_id,
            script=script,
            metadata={**options, "storage_uri": storage_uri},
            prompt_chars=len(prompt),
            storage_uri=storage_uri,
            created_at=created_at,
        )
        return self.script_repository.save_script(record.model_dump())


class AudioGenerationService:
    def __init__(
        self,
        storage: AudioStorage,
        script_repository: ScriptRepository,
        audio_repository: AudioRepository,
        renderer: AudioRenderer,
        speech_provider: str,
    ) -> None:
        self.storage = storage
        self.script_repository = script_repository
        self.audio_repository = audio_repository
        self.renderer = renderer
        self.speech_provider = speech_provider

    def generate_audio(
        self,
        user_id: str,
        script_id: str,
        voice_style: VoiceStyle,
        speed: SpeechSpeed,
    ) -> dict:
        script_record = self.script_repository.get_script(script_id, user_id)
        if script_record is None:
            raise AppError(
                "SCRIPT_NOT_FOUND",
                "Generated script was not found.",
                status_code=404,
                detail={"script_id": script_id},
            )

        render_options = AudioRenderOptions(
            speech=SpeechOptions(
                provider=self.speech_provider,
                personality=voice_style,
                speed=speed,
            )
        )
        audio_asset = self.renderer.render(script_record["script"], render_options)
        audio_id = new_id("audio")
        storage_uri, audio_url = self.storage.save_audio(user_id, audio_id, audio_asset)
        record = AudioRecord(
            audio_id=audio_id,
            user_id=user_id,
            script_id=script_id,
            audio_url=audio_url,
            audio_format=audio_asset.format,
            media_type=audio_asset.media_type,
            voice_style=voice_style,
            speed=speed,
            metadata={
                "speech": render_options.speech.model_dump(exclude={"voice_name"}),
                "voice_name": render_options.speech.voice_name,
            },
            storage_uri=storage_uri,
            created_at=utc_now_iso(),
        )
        return self.audio_repository.save_audio(record.model_dump())

