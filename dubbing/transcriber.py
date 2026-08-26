"""Speech-to-text using faster-whisper with CPU/CUDA auto-detection."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class TranscriptSegment:
    """A timestamped source-language speech segment."""

    index: int
    start_time: float
    end_time: float
    text: str
    language: str | None = None

    @property
    def duration(self) -> float:
        """Return segment duration in seconds."""

        return max(0.0, self.end_time - self.start_time)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)


def detect_device(requested: str = "auto") -> str:
    """Resolve the requested device to ``cpu`` or ``cuda``."""

    if requested in {"cpu", "cuda"}:
        return requested
    if requested != "auto":
        raise ValueError("WHISPER_DEVICE faqat auto, cpu yoki cuda bo‘lishi mumkin.")

    visible_devices = os.getenv("CUDA_VISIBLE_DEVICES")
    if shutil.which("nvidia-smi") and visible_devices != "-1":
        probe = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0 and probe.stdout.strip():
            return "cuda"
    return "cpu"


def detect_compute_type(device: str, requested: str = "auto") -> str:
    """Choose a safe CTranslate2 compute type for the selected device."""

    if requested != "auto":
        return requested
    return "float16" if device == "cuda" else "int8"


def transcribe(
    audio_path: str | Path,
    model_name: str = "medium",
    language: str = "auto",
    device: str = "auto",
    compute_type: str = "auto",
) -> tuple[list[TranscriptSegment], str | None]:
    """Transcribe audio and return timestamped segments plus detected language."""

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper o‘rnatilmagan. `pip install -r dubbing/requirements.txt` ni bajaring."
        ) from exc

    resolved_device = detect_device(device)
    resolved_compute = detect_compute_type(resolved_device, compute_type)
    model = WhisperModel(model_name, device=resolved_device, compute_type=resolved_compute)
    requested_language = None if language == "auto" else language
    segments, info = model.transcribe(
        str(audio_path),
        language=requested_language,
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=False,
    )

    result: list[TranscriptSegment] = []
    detected_language = getattr(info, "language", None)
    for index, segment in enumerate(segments):
        text = segment.text.strip()
        if not text:
            continue
        result.append(
            TranscriptSegment(
                index=index,
                start_time=round(float(segment.start), 3),
                end_time=round(float(segment.end), 3),
                text=text,
                language=detected_language,
            )
        )
    return result, detected_language
