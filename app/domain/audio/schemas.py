from typing import Literal

from pydantic import BaseModel, Field


AudioFormat = Literal["wav", "mp3"]
SpeechPersonality = Literal["friendly", "professor"]
VoiceStyle = SpeechPersonality
SpeechSpeed = Literal["slow", "normal", "fast"]
MusicMood = Literal["none", "calm", "bright", "focused", "dramatic"]


class AudioAsset(BaseModel):
    content: bytes
    format: AudioFormat
    media_type: str


class SpeechOptions(BaseModel):
    provider: str = "gemini"
    personality: SpeechPersonality = "friendly"
    speed: SpeechSpeed = "normal"
    voice_name: str | None = None


class MusicOptions(BaseModel):
    enabled: bool = False
    mood: MusicMood = "none"
    volume: float = Field(default=0.15, ge=0.0, le=1.0)


class MixOptions(BaseModel):
    speech_volume: float = Field(default=1.0, ge=0.0, le=1.0)
    music_volume: float = Field(default=0.15, ge=0.0, le=1.0)


class AudioRenderOptions(BaseModel):
    output_format: AudioFormat = "wav"
    speech: SpeechOptions = Field(default_factory=SpeechOptions)
    music: MusicOptions = Field(default_factory=MusicOptions)
    mix: MixOptions = Field(default_factory=MixOptions)


class TTSOptions(BaseModel):
    voice_style: VoiceStyle
    speed: SpeechSpeed = "normal"

    def to_render_options(self, provider: str = "gemini") -> AudioRenderOptions:
        return AudioRenderOptions(
            speech=SpeechOptions(
                provider=provider,
                personality=self.voice_style,
                speed=self.speed,
            )
        )


class TTSGenerateRequest(TTSOptions):
    script_id: str


class TTSGenerateResponse(BaseModel):
    audio_id: str
    audio_url: str

