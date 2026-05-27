from app.domain.audio.schemas import AudioAsset, AudioRenderOptions


class PassthroughAudioMixer:
    def mix(
        self,
        speech: AudioAsset,
        music: AudioAsset | None,
        options: AudioRenderOptions,
    ) -> AudioAsset:
        return speech

