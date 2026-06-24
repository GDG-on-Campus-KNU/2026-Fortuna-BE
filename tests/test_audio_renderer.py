import io
import wave
from unittest.mock import Mock

from app.domain.audio.renderer import AudioRenderer
from app.domain.audio.schemas import AudioAsset, AudioRenderOptions, SpeechOptions


def make_mock_wav(n_frames: int = 100) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        # 1 frame is 2 bytes for 16-bit mono
        w.writeframes(b"\x00\x00" * n_frames)
    return out.getvalue()


def test_split_script_into_chunks_under_limit():
    renderer = AudioRenderer(Mock(), Mock(), Mock())
    script = "안녕하세요. 오늘 날씨가 참 좋습니다! 새로운 팟캐스트입니다."
    # Total words: 2 + 4 + 2 = 8 words.
    chunks = renderer._split_script_into_chunks(script, max_words=300)
    assert chunks == ["안녕하세요. 오늘 날씨가 참 좋습니다! 새로운 팟캐스트입니다."]


def test_split_script_into_chunks_over_limit():
    renderer = AudioRenderer(Mock(), Mock(), Mock())
    # Create text with 4 sentences, each containing 3 words (total 12 words)
    # Target max_words = 6. Should group into 2 chunks of 6 words each.
    script = "하나 둘 셋. 넷 다섯 여섯. 일곱 여덟 아홉. 열 열하나 열둘."
    chunks = renderer._split_script_into_chunks(script, max_words=6)
    
    assert len(chunks) == 2
    assert chunks[0] == "하나 둘 셋. 넷 다섯 여섯."
    assert chunks[1] == "일곱 여덟 아홉. 열 열하나 열둘."



def test_split_script_into_chunks_empty():
    renderer = AudioRenderer(Mock(), Mock(), Mock())
    assert renderer._split_script_into_chunks("", max_words=300) == []
    assert renderer._split_script_into_chunks("   ", max_words=300) == []


def test_split_script_into_chunks_single_huge_sentence():
    renderer = AudioRenderer(Mock(), Mock(), Mock())
    # A single sentence with 10 words, target max_words = 5.
    # Because there are no sentence terminators inside, it will be treated as one sentence.
    script = "하나 둘 셋 넷 다섯 여섯 일곱 여덟 아홉 열."
    chunks = renderer._split_script_into_chunks(script, max_words=5)
    assert chunks == ["하나 둘 셋 넷 다섯 여섯 일곱 여덟 아홉 열."]


def test_concatenate_wav_contents():
    renderer = AudioRenderer(Mock(), Mock(), Mock())
    wav1 = make_mock_wav(n_frames=100)
    wav2 = make_mock_wav(n_frames=150)
    
    concatenated = renderer._concatenate_wav_contents([wav1, wav2])
    
    # Read the concatenated WAV and verify frames and params
    with wave.open(io.BytesIO(concatenated), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == 24000
        assert w.getnframes() == 250


def test_concatenate_speech_assets_mp3():
    renderer = AudioRenderer(Mock(), Mock(), Mock())
    asset1 = AudioAsset(content=b"mp3_part_1", format="mp3", media_type="audio/mpeg")
    asset2 = AudioAsset(content=b"mp3_part_2", format="mp3", media_type="audio/mpeg")
    
    concatenated = renderer._concatenate_speech_assets([asset1, asset2])
    
    assert concatenated.format == "mp3"
    assert concatenated.media_type == "audio/mpeg"
    assert concatenated.content == b"mp3_part_1mp3_part_2"


def test_render_end_to_end_wav():
    speech_synthesizer = Mock()
    music_generator = Mock()
    mixer = Mock()
    
    renderer = AudioRenderer(speech_synthesizer, music_generator, mixer)
    
    # Prepare synthesiser mocks to return wav assets
    wav1 = make_mock_wav(50)
    wav2 = make_mock_wav(50)
    
    asset1 = AudioAsset(content=wav1, format="wav", media_type="audio/wav")
    asset2 = AudioAsset(content=wav2, format="wav", media_type="audio/wav")
    
    speech_synthesizer.synthesize.side_effect = [asset1, asset2]
    music_generator.generate.return_value = None
    
    # Mixer should just return the speech it is given
    mixer.mix.side_effect = lambda speech, music, options: speech
    
    script = "하나 둘 셋. 넷 다섯 여섯."
    options = AudioRenderOptions(
        speech=SpeechOptions(provider="gemini", personality="friendly", speed="normal")
    )
    
    # Run with max_words limit = 4, so it splits into two chunks:
    # "하나 둘 셋." (3 words) and "넷 다섯 여섯." (3 words)
    # We temporarily patch or override _split_script_into_chunks to verify it works,
    # or just call it directly. Let's patch _split_script_into_chunks target words limit in test:
    original_split = renderer._split_script_into_chunks
    renderer._split_script_into_chunks = lambda s, max_words: original_split(s, max_words=4)
    
    result = renderer.render(script, options)
    
    # Verify synthesize was called twice
    assert speech_synthesizer.synthesize.call_count == 2
    speech_synthesizer.synthesize.assert_any_call("하나 둘 셋.", options.speech)
    speech_synthesizer.synthesize.assert_any_call("넷 다섯 여섯.", options.speech)
    
    # Verify concatenated output
    with wave.open(io.BytesIO(result.content), "rb") as w:
        assert w.getnframes() == 100
        assert result.format == "wav"
