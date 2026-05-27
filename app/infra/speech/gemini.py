import base64
import io
import wave

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.audio.schemas import AudioAsset, SpeechOptions


class GeminiSpeechSynthesizer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def synthesize(self, script: str, options: SpeechOptions) -> AudioAsset:
        if not self.settings.gemini_api_key:
            raise AppError(
                "TTS_GENERATION_FAILED",
                "GEMINI_API_KEY is not configured.",
                status_code=503,
            )
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.settings.gemini_api_key)
            response = client.models.generate_content(
                model=self.settings.gemini_tts_model,
                contents=self._prompt(script, options),
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self._voice_name(options)
                            )
                        )
                    ),
                ),
            )
            inline_data = (
                response.candidates[0].content.parts[0].inline_data
                if response.candidates
                else None
            )
            pcm = inline_data.data if inline_data else None
        except Exception as exc:
            raise AppError(
                "TTS_GENERATION_FAILED",
                "Failed to generate audio with Gemini TTS.",
                status_code=502,
                detail={"reason": exc.__class__.__name__},
            ) from exc
        if not pcm:
            raise AppError(
                "TTS_GENERATION_FAILED",
                "Gemini TTS returned empty audio.",
                status_code=502,
            )
        pcm_bytes = self._to_bytes(pcm)
        return AudioAsset(
            content=self._wrap_pcm_as_wav(pcm_bytes),
            format="wav",
            media_type="audio/wav",
        )

    def _voice_name(self, options: SpeechOptions) -> str:
        if options.voice_name:
            return options.voice_name
        return {
            "friendly": self.settings.gemini_tts_friendly_voice_name,
            "professor": self.settings.gemini_tts_professor_voice_name,
        }[options.personality]

    def _prompt(self, script: str, options: SpeechOptions) -> str:
        style_instruction = {
            "friendly": "Read warmly and naturally, like a friendly study partner.",
            "professor": "Read calmly and clearly, like a professor explaining a concept.",
        }[options.personality]
        speed_instruction = {
            "slow": "Keep the pace slow.",
            "normal": "Keep the pace natural.",
            "fast": "Keep the pace slightly fast.",
        }[options.speed]
        return (
            f"{style_instruction} {speed_instruction} "
            "Read the following Korean learning podcast script exactly as narration.\n\n"
            f"{script}"
        )

    def _to_bytes(self, data: bytes | str) -> bytes:
        if isinstance(data, bytes):
            return data
        return base64.b64decode(data)

    def _wrap_pcm_as_wav(self, pcm: bytes) -> bytes:
        output = io.BytesIO()
        with wave.open(output, "wb") as wav_file:
            wav_file.setnchannels(self.settings.gemini_tts_channels)
            wav_file.setsampwidth(self.settings.gemini_tts_sample_width)
            wav_file.setframerate(self.settings.gemini_tts_sample_rate_hz)
            wav_file.writeframes(pcm)
        return output.getvalue()

