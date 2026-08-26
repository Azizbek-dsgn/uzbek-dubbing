"""Input resolution and audio extraction helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence


VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}


def _run(command: Sequence[str]) -> None:
    """Run a command and expose a readable error when it fails."""

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-2000:]
        raise RuntimeError(f"Buyruq bajarilmadi: {' '.join(command)}\n{detail}")


def is_url(value: str) -> bool:
    """Return whether a string looks like an HTTP(S) URL."""

    return value.startswith(("http://", "https://"))


def download_audio(url: str, destination: str | Path) -> Path:
    """Download the best available audio stream from a URL with yt-dlp."""

    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    output_template = str(target.with_suffix("")) + ".%(ext)s"
    command = [
        "yt-dlp",
        "--no-playlist",
        "-f",
        "bestaudio/best",
        "-o",
        output_template,
        url,
    ]
    _run(command)
    candidates = sorted(target.parent.glob(target.stem + ".*"))
    candidates = [path for path in candidates if path.suffix not in {".part", ".ytdl"}]
    if not candidates:
        raise RuntimeError("URL’dan audio fayl yuklab olinmadi.")
    return candidates[0]


def extract_wav(source: str | Path, destination: str | Path, ffmpeg: str = "ffmpeg") -> Path:
    """Convert a local audio/video source to a 16 kHz mono PCM WAV file."""

    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"Input fayl topilmadi: {source_path}")

    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(source_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(target),
        ]
    )
    return target


def download_media(url: str, destination: str | Path) -> Path:
    """Download a best-quality single video with audio for final muxing."""

    target = Path(destination).with_suffix(".mp4")
    target.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "yt-dlp",
            "--no-playlist",
            "-f",
            "bv*+ba/b",
            "--merge-output-format",
            "mp4",
            "-o",
            str(target),
            url,
        ]
    )
    if not target.exists():
        raise RuntimeError("URL’dan video fayl yuklab olinmadi.")
    return target


def resolve_source(source: str, work_dir: str | Path, ffmpeg: str = "ffmpeg") -> tuple[Path, Path | None]:
    """Resolve a URL or local media file and return (wav_path, original_media)."""

    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    original_media: Path | None

    if is_url(source):
        downloaded = download_media(source, work / "source_video")
        original_media = downloaded
        wav_source = downloaded
    else:
        local = Path(source).expanduser().resolve()
        if not local.exists():
            raise FileNotFoundError(f"Input fayl topilmadi: {local}")
        original_media = local if local.suffix.lower() in VIDEO_SUFFIXES else None
        wav_source = local

    wav_path = work / "source.wav"
    extract_wav(wav_source, wav_path, ffmpeg=ffmpeg)
    return wav_path, original_media
