"""Timeline assembly and video/audio muxing."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence

from pydub import AudioSegment


def _run(command: Sequence[str]) -> None:
    """Run FFmpeg and raise a concise error on failure."""

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-2500:]
        raise RuntimeError(f"FFmpeg xatosi:\n{detail}")


def build_dubbing_track(
    segments: list[dict],
    segment_audio_paths: list[str | Path],
    output_path: str | Path,
    frame_rate: int = 24000,
) -> Path:
    """Place each fitted segment on its original timeline and export WAV."""

    if len(segments) != len(segment_audio_paths):
        raise ValueError("Segmentlar soni va audio fayllar soni teng bo‘lishi kerak.")
    if not segments:
        raise ValueError("Dublyaj uchun segmentlar topilmadi.")

    total_ms = max(round(float(item["end_time"]) * 1000) for item in segments)
    track = AudioSegment.silent(duration=max(total_ms, 1), frame_rate=frame_rate)
    for segment, audio_path in zip(segments, segment_audio_paths):
        clip = AudioSegment.from_file(audio_path).set_frame_rate(frame_rate)
        position_ms = max(0, round(float(segment["start_time"]) * 1000))
        track = track.overlay(clip, position=position_ms)

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    track.export(target, format="wav")
    return target


def _has_audio_stream(video_path: str | Path, ffprobe: str = "ffprobe") -> bool:
    """Check whether a media file contains at least one audio stream."""

    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            str(video_path),
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def mux_with_video(
    video_path: str | Path,
    dubbing_track: str | Path,
    output_path: str | Path,
    ffmpeg: str = "ffmpeg",
) -> Path:
    """Mix Uzbek speech over quiet original audio and copy the video stream."""

    video = Path(video_path)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if _has_audio_stream(video):
        command = [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-i",
            str(dubbing_track),
            "-filter_complex",
            "[0:a:0]volume=0.22[background];"
            "[1:a:0]volume=1.0[voice];"
            "[background][voice]amix=inputs=2:duration=longest:dropout_transition=2[mix]",
            "-map",
            "0:v:0",
            "-map",
            "[mix]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(target),
        ]
    else:
        command = [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-i",
            str(dubbing_track),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(target),
        ]
    _run(command)
    return target
