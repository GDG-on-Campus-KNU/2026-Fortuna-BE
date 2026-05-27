from app.core.config import Settings
from app.core.errors import AppError
from app.domain.audio.schemas import AudioAsset, SpeechOptions, SpeechSpeed, VoiceStyle


class GoogleCloudSpeechSynthesizer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def synthesize(self, script: str, options: SpeechOptions) -> AudioAsset:
        try:
            from google.cloud import texttospeech

            client = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(text=script)
            voice_options = {
                "language_code": self.settings.google_tts_language_code,
            }
            if options.voice_name or self.settings.google_tts_voice_name:
                voice_options["name"] = (
                    options.voice_name or self.settings.google_tts_voice_name
                )
            voice = texttospeech.VoiceSelectionParams(**voice_options)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=getattr(
                    texttospeech.AudioEncoding,
                    self.settings.google_tts_audio_encoding or "MP3",
                ),
                speaking_rate=self._speaking_rate(options.personality, options.speed),
                pitch=self._pitch(options.personality),
            )
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
        except Exception as exc:
            raise AppError(
                "TTS_GENERATION_FAILED",
                "Failed to generate audio with Google Cloud Text-to-Speech.",
                status_code=502,
                detail={"reason": exc.__class__.__name__},
            ) from exc
        if not response.audio_content:
            raise AppError(
                "TTS_GENERATION_FAILED",
                "Google Cloud Text-to-Speech returned empty audio.",
                status_code=502,
            )

        if (self.settings.google_tts_audio_encoding or "MP3") == "LINEAR16":
            audio_format = "wav"
            media_type = "audio/wav"
        else:
            audio_format = "mp3"
            media_type = "audio/mpeg"
        return AudioAsset(
            content=response.audio_content,
            format=audio_format,
            media_type=media_type,
        )

    def _speaking_rate(self, personality: VoiceStyle, speed: SpeechSpeed) -> float:
        speed_multiplier = {"slow": 0.88, "normal": 1.0, "fast": 1.12}[speed]
        style_multiplier = {"friendly": 1.03, "professor": 0.96}[personality]
        return self.settings.google_tts_speaking_rate * speed_multiplier * style_multiplier

    def _pitch(self, personality: VoiceStyle) -> float:
        style_pitch = {"friendly": 1.0, "professor": -1.0}[personality]
        return self.settings.google_tts_pitch + style_pitch

