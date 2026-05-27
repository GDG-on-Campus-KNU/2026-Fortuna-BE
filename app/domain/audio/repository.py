from typing import Protocol

from app.domain.audio.schemas import AudioAsset, AudioRenderOptions, MusicOptions, SpeechOptions


class SpeechSynthesizer(Protocol):
    def synthesize(self, script: str, options: SpeechOptions) -> AudioAsset: ...


class MusicGenerator(Protocol):
    def generate(self, options: MusicOptions) -> AudioAsset | None: ...


class AudioMixer(Protocol):
    def mix(
        self,
        speech: AudioAsset,
        music: AudioAsset | None,
        options: AudioRenderOptions,
    ) -> AudioAsset: ...


class AudioStorage(Protocol):
    def save_audio(self, user_id: str, audio_id: str, asset: AudioAsset) -> tuple[str, str]: ...


class AudioRepository(Protocol):
    def save_audio(self, record: dict) -> dict: ...

    def get_audio(self, audio_id: str, user_id: str | None = None) -> dict | None: ...

    def list_audio(self, user_id: str) -> list[dict]: ...

