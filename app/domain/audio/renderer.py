from app.domain.audio.repository import AudioMixer, MusicGenerator, SpeechSynthesizer
from app.domain.audio.schemas import AudioAsset, AudioRenderOptions


class AudioRenderer:
    def __init__(
        self,
        speech_synthesizer: SpeechSynthesizer,
        music_generator: MusicGenerator,
        mixer: AudioMixer,
    ) -> None:
        self.speech_synthesizer = speech_synthesizer
        self.music_generator = music_generator
        self.mixer = mixer

    def render(self, script: str, options: AudioRenderOptions) -> AudioAsset:
        speech = self.speech_synthesizer.synthesize(script, options.speech)
        music = self.music_generator.generate(options.music)
        return self.mixer.mix(speech, music, options)

