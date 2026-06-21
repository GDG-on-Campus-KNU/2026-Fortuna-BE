import base64
import io
from pathlib import Path
import re
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

        friendly_voice = self.settings.gemini_tts_friendly_voice_name
        if not friendly_voice or friendly_voice == "Puck":
            friendly_voice = "Zephyr"

        professor_voice = self.settings.gemini_tts_professor_voice_name
        if not professor_voice or professor_voice == "Kore":
            professor_voice = "Algieba"

        return {
            "friendly": friendly_voice,
            "professor": professor_voice,
        }[options.personality]

    def _prompt(self, script: str, options: SpeechOptions) -> str:
        content = self._load_prompt_file(options.personality)

        # Replace pacing details based on speed
        if options.personality == "friendly":
            pacing_text = {
                "slow": "Pacing:\n- Slow conversational pace.",
                "normal": "Pacing:\n- Easy, natural conversational pace with light variation.\n- Brief, comfortable pauses where a friend would naturally pause.",
                "fast": "Pacing:\n- Rapid conversational pace with minimal pauses.",
            }[options.speed]
        else:  # professor
            pacing_text = {
                "slow": "Pacing:\n- Slow pace.\n- Use longer reflective pauses before important concepts.",
                "normal": "Pacing:\n- Slow to moderately slow.\n- Use short reflective pauses before important concepts.\n- Do not rush through technical terms.\n- Maintain a steady lecture-like rhythm.",
                "fast": "Pacing:\n- Normal/moderate pace.\n- Maintain a steady lecture-like rhythm.",
            }[options.speed]

        content = re.sub(
            r"Pacing:[\s\S]*?(?=(Pitch and Intonation:|Voice quality:))",
            pacing_text + "\n",
            content,
        )

        return f"{content}\n{script}"

    def _load_prompt_file(self, personality: str) -> str:
        try:
            prompt_file = Path(__file__).parent / "prompt" / f"{personality}.md"
            return prompt_file.read_text(encoding="utf-8").strip()
        except Exception as exc:
            raise AppError(
                "TTS_GENERATION_FAILED",
                f"Failed to load prompt file for {personality}.",
                status_code=500,
                detail={"reason": str(exc)},
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
