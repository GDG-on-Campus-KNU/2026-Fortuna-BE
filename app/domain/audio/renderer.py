from concurrent.futures import ThreadPoolExecutor
import io
import re
import wave

from app.core.errors import AppError
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
        chunks = self._split_script_into_chunks(script, max_words=150)

        if not chunks:
            speech = self.speech_synthesizer.synthesize("", options.speech)
        else:
            with ThreadPoolExecutor() as executor:
                speech_assets = list(
                    executor.map(
                        lambda chunk: self.speech_synthesizer.synthesize(chunk, options.speech),
                        chunks,
                    )
                )

            speech = self._concatenate_speech_assets(speech_assets)


        music = self.music_generator.generate(options.music)
        return self.mixer.mix(speech, music, options)

    def _split_script_into_chunks(self, script: str, max_words: int) -> list[str]:
        # Split by sentence terminators followed by spaces, or on newlines
        raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", script)
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        chunks = []
        current_chunk = []
        current_word_count = 0

        for sentence in sentences:
            word_count = len(sentence.split())
            if current_word_count + word_count > max_words:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = [sentence]
                    current_word_count = word_count
                else:
                    # If a single sentence exceeds the target size, it is a single chunk
                    chunks.append(sentence)
                    current_chunk = []
                    current_word_count = 0
            else:
                current_chunk.append(sentence)
                current_word_count += word_count

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _concatenate_speech_assets(self, assets: list[AudioAsset]) -> AudioAsset:
        if not assets:
            raise AppError("TTS_GENERATION_FAILED", "No audio assets generated to concatenate.")

        if len(assets) == 1:
            return assets[0]

        first_asset = assets[0]
        audio_format = first_asset.format
        media_type = first_asset.media_type

        if audio_format == "wav":
            content = self._concatenate_wav_contents([a.content for a in assets])
        else:
            # MP3 or other format, concatenate bytes directly
            content = b"".join([a.content for a in assets])

        return AudioAsset(
            content=content,
            format=audio_format,
            media_type=media_type,
        )

    def _concatenate_wav_contents(self, wav_contents: list[bytes]) -> bytes:
        first_wav = io.BytesIO(wav_contents[0])
        try:
            with wave.open(first_wav, "rb") as wav_in:
                params = wav_in.getparams()
        except Exception as exc:
            raise AppError(
                "TTS_GENERATION_FAILED",
                "Failed to parse WAV parameters for concatenation.",
                status_code=500,
                detail={"reason": str(exc)},
            ) from exc

        output = io.BytesIO()
        try:
            with wave.open(output, "wb") as wav_out:
                wav_out.setparams(params)
                for content in wav_contents:
                    wav_in_io = io.BytesIO(content)
                    with wave.open(wav_in_io, "rb") as wav_in:
                        wav_out.writeframes(wav_in.readframes(wav_in.getnframes()))
        except Exception as exc:
            raise AppError(
                "TTS_GENERATION_FAILED",
                "Failed to concatenate WAV audio contents.",
                status_code=500,
                detail={"reason": str(exc)},
            ) from exc

        return output.getvalue()


