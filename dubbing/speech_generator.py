"""Uzbek neural speech generation and segment time fitting."""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydub import AudioSegment

from .translator import TranslationSegment

VOICE_ALIASES = {
    "sardor": "uz-UZ-SardorNeural",
    "madina": "uz-UZ-MadinaNeural",
    "uz-UZ-SardorNeural": "uz-UZ-SardorNeural",
    "uz-UZ-MadinaNeural": "uz-UZ-MadinaNeural",
}


def resolve_voice(voice: str) -> str:
    """Resolve a friendly voice alias to an Edge-TTS voice name."""

    try:
        return VOICE_ALIASES[voice]
    except KeyError as exc:
        supported = ", ".join(sorted(VOICE_ALIASES))
        raise ValueError(f"Noma’lum ovoz: {voice}. Mavjud ovozlar: {supported}") from exc


def fit_audio_to_duration(audio: AudioSegment, target_seconds: float) -> AudioSegment:
    """Time-fit audio using a bounded 0.9x–1.15x stretch, then exact trim/pad."""

    target_ms = max(1, round(target_seconds * 1000))
    if len(audio) == 0:
        return AudioSegment.silent(duration=target_ms, frame_rate=24000)

    ratio = len(audio) / target_ms
    speed = min(1.15, max(0.9, ratio))
    adjusted_rate = max(1000, round(audio.frame_rate * speed))
    stretched = audio._spawn(audio.raw_data, overrides={"frame_rate": adjusted_rate})
    stretched = stretched.set_frame_rate(audio.frame_rate)

    if len(stretched) > target_ms:
        return stretched[:target_ms]
    if len(stretched) < target_ms:
        return stretched + AudioSegment.silent(
            duration=target_ms - len(stretched),
            frame_rate=stretched.frame_rate,
        )
    return stretched


async def synthesize_one(text: str, voice: str, output_path: str | Path) -> Path:
    """Synthesize one Uzbek text segment to MP3 using Edge-TTS."""

    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError(
            "edge-tts o‘rnatilmagan. `pip install -r dubbing/requirements.txt` ni bajaring."
        ) from exc

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    communication = edge_tts.Communicate(text=text, voice=resolve_voice(voice))
    await communication.save(str(target))
    return target


def prepare_segment_audio(
    source_mp3: str | Path,
    target_wav: str | Path,
    duration: float,
) -> Path:
    """Fit an Edge-TTS MP3 to the original segment duration and save WAV."""

    audio = AudioSegment.from_file(source_mp3)
    fitted = fit_audio_to_duration(audio, duration)
    target = Path(target_wav)
    target.parent.mkdir(parents=True, exist_ok=True)
    fitted.export(target, format="wav")
    return target


async def generate_segment_audio(
    segment: TranslationSegment,
    voice: str,
    output_dir: str | Path,
) -> Path:
    """Generate and time-fit one translated segment."""

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / f"segment_{segment.index:05d}.mp3"
    fitted_path = directory / f"segment_{segment.index:05d}.wav"
    await synthesize_one(segment.translated_text, voice, raw_path)
    return prepare_segment_audio(raw_path, fitted_path, segment.duration)


def generate_all_segments(
    segments: list[TranslationSegment],
    voice: str,
    output_dir: str | Path,
) -> list[Path]:
    """Generate segment audio sequentially to avoid provider throttling."""

    async def runner() -> list[Path]:
        paths: list[Path] = []
        for segment in segments:
            paths.append(await generate_segment_audio(segment, voice, output_dir))
        return paths

    return asyncio.run(runner())
