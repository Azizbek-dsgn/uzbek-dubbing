"""Configuration and runtime checks for the Uzbek dubbing pipeline."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    whisper_model: str = "medium"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"
    default_voice: str = "uz-UZ-SardorNeural"
    work_dir: Path = Path(".dubbing_work")
    max_translation_retries: int = 3


def load_settings(env_file: str | Path | None = None) -> Settings:
    """Load settings from a .env file and the process environment."""

    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY topilmadi. .env fayliga Gemini API kalitini yozing."
        )

    return Settings(
        gemini_api_key=api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
        whisper_model=os.getenv("WHISPER_MODEL", "medium").strip(),
        whisper_device=os.getenv("WHISPER_DEVICE", "auto").strip(),
        whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "auto").strip(),
        default_voice=os.getenv("DUBBING_VOICE", "uz-UZ-SardorNeural").strip(),
        work_dir=Path(os.getenv("DUBBING_WORK_DIR", ".dubbing_work")),
        max_translation_retries=int(os.getenv("MAX_TRANSLATION_RETRIES", "3")),
    )


def require_ffmpeg() -> str:
    """Return the FFmpeg executable or raise a clear setup error."""

    executable = shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError(
            "FFmpeg topilmadi. Ubuntu/Debian: sudo apt install ffmpeg; "
            "macOS: brew install ffmpeg; Windows: ffmpeg.org orqali o‘rnating."
        )
    return executable


def ensure_work_dir(settings: Settings) -> Path:
    """Create and return the working directory used for checkpoints and segments."""

    settings.work_dir.mkdir(parents=True, exist_ok=True)
    return settings.work_dir
