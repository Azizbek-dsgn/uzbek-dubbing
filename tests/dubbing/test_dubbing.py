from pathlib import Path

from pydub import AudioSegment

from dubbing.checkpoints import load_checkpoint, save_checkpoint
from dubbing.speech_generator import fit_audio_to_duration, resolve_voice


def test_fit_audio_to_duration_is_exact():
    source = AudioSegment.silent(duration=2_000, frame_rate=24_000)
    fitted = fit_audio_to_duration(source, 1.5)
    assert abs(len(fitted) - 1_500) <= 1


def test_fit_audio_to_duration_pads_short_audio():
    source = AudioSegment.silent(duration=500, frame_rate=24_000)
    fitted = fit_audio_to_duration(source, 1.5)
    assert abs(len(fitted) - 1_500) <= 1


def test_voice_aliases():
    assert resolve_voice("sardor") == "uz-UZ-SardorNeural"
    assert resolve_voice("madina") == "uz-UZ-MadinaNeural"


def test_checkpoint_is_atomic_and_round_trips(tmp_path: Path):
    path = tmp_path / "checkpoint.json"
    save_checkpoint(path, {"stage": "translation", "items": [1, 2]})
    assert load_checkpoint(path) == {"stage": "translation", "items": [1, 2]}
    assert not path.with_suffix(".json.tmp").exists()
