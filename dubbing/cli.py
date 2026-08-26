"""Command-line entrypoint for English/Russian to Uzbek dubbing."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import shutil
from pathlib import Path
from typing import Any

from .audio_extractor import resolve_source
from .audio_mixer import build_dubbing_track, mux_with_video
from .checkpoints import load_checkpoint, save_checkpoint
from .config import ensure_work_dir, load_settings, require_ffmpeg
from .speech_generator import generate_segment_audio, resolve_voice
from .transcriber import TranscriptSegment, transcribe
from .translator import GeminiTranslator, TranslationSegment

LOGGER = logging.getLogger("uzbek_dubbing")


def _transcript_from_dict(item: dict[str, Any]) -> TranscriptSegment:
    """Deserialize one transcript segment from a checkpoint."""

    return TranscriptSegment(
        index=int(item["index"]),
        start_time=float(item["start_time"]),
        end_time=float(item["end_time"]),
        text=str(item["text"]),
        language=item.get("language"),
    )


def _translation_from_dict(item: dict[str, Any]) -> TranslationSegment:
    """Deserialize one translation segment from a checkpoint."""

    return TranslationSegment(
        index=int(item["index"]),
        start_time=float(item["start_time"]),
        end_time=float(item["end_time"]),
        source_text=str(item["source_text"]),
        translated_text=str(item["translated_text"]),
        language=item.get("language"),
    )


async def _generate_audio_with_resume(
    segments: list[TranslationSegment],
    voice: str,
    output_dir: Path,
    checkpoint_path: Path,
    checkpoint: dict[str, Any],
) -> list[Path]:
    """Generate fitted segment files one by one and checkpoint each result."""

    audio_cache = checkpoint.setdefault("audio", {})
    paths: list[Path] = []
    for segment in segments:
        cached_path = Path(audio_cache.get(str(segment.index), ""))
        if cached_path.exists():
            path = cached_path
        else:
            path = await generate_segment_audio(segment, voice, output_dir)
            audio_cache[str(segment.index)] = str(path)
            save_checkpoint(checkpoint_path, checkpoint)
        paths.append(path)
        LOGGER.info("TTS segment %s/%s tayyor", segment.index + 1, len(segments))
    return paths


def run_pipeline(args: argparse.Namespace) -> Path:
    """Run extraction, STT, translation, TTS, mixing and final muxing."""

    settings = load_settings(args.env_file)
    ffmpeg = require_ffmpeg()
    settings = settings.__class__(
        **{
            **settings.__dict__,
            "work_dir": Path(args.work_dir or settings.work_dir),
        }
    )
    work_dir = ensure_work_dir(settings)
    checkpoint_path = work_dir / "checkpoint.json"
    checkpoint = load_checkpoint(checkpoint_path) or {}
    checkpoint["source"] = args.input
    checkpoint["voice"] = resolve_voice(args.voice)
    checkpoint["language"] = args.lang
    save_checkpoint(checkpoint_path, checkpoint)

    wav_path, original_media = resolve_source(args.input, work_dir, ffmpeg=ffmpeg)
    checkpoint["source_wav"] = str(wav_path)
    checkpoint["original_media"] = str(original_media) if original_media else None
    save_checkpoint(checkpoint_path, checkpoint)

    if checkpoint.get("transcript"):
        transcript = [_transcript_from_dict(item) for item in checkpoint["transcript"]]
        detected_language = checkpoint.get("detected_language")
        LOGGER.info("Transkripsiya checkpoint’dan yuklandi: %s segment", len(transcript))
    else:
        transcript, detected_language = transcribe(
            wav_path,
            model_name=args.whisper_model or settings.whisper_model,
            language=args.lang,
            device=args.device or settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        checkpoint["transcript"] = [segment.to_dict() for segment in transcript]
        checkpoint["detected_language"] = detected_language
        save_checkpoint(checkpoint_path, checkpoint)
        LOGGER.info("Transkripsiya tugadi: %s segment, til=%s", len(transcript), detected_language)

    if not transcript:
        raise RuntimeError("Nutq segmentlari topilmadi; audio faylni tekshiring.")

    translation_cache = {
        int(item["index"]): str(item["translated_text"])
        for item in checkpoint.get("translations", [])
        if item.get("translated_text")
    }
    translator = GeminiTranslator(
        settings.gemini_api_key,
        model=settings.gemini_model,
        retries=settings.max_translation_retries,
    )
    translations: list[TranslationSegment] = []
    for segment in transcript:
        translated = translation_cache.get(segment.index)
        if not translated:
            translated = translator.translate_one(
                segment.text,
                segment.language or detected_language,
                segment.duration,
            )
            translation_cache[segment.index] = translated
            checkpoint["translations"] = [
                {
                    "index": item.index,
                    "start_time": item.start_time,
                    "end_time": item.end_time,
                    "source_text": item.text,
                    "translated_text": translation_cache.get(item.index, ""),
                    "language": item.language or detected_language,
                }
                for item in transcript
                if translation_cache.get(item.index)
            ]
            save_checkpoint(checkpoint_path, checkpoint)
        translations.append(
            TranslationSegment(
                index=segment.index,
                start_time=segment.start_time,
                end_time=segment.end_time,
                source_text=segment.text,
                translated_text=translated,
                language=segment.language or detected_language,
            )
        )
        LOGGER.info("Tarjima segment %s/%s tayyor", segment.index + 1, len(transcript))

    segment_dir = work_dir / "segments"
    audio_paths = asyncio.run(
        _generate_audio_with_resume(
            translations,
            resolve_voice(args.voice),
            segment_dir,
            checkpoint_path,
            checkpoint,
        )
    )

    track_path = Path(checkpoint.get("dubbing_track", work_dir / "dubbing_track.wav"))
    if not track_path.exists():
        track_path = build_dubbing_track(
            [item.to_dict() for item in translations],
            audio_paths,
            track_path,
        )
        checkpoint["dubbing_track"] = str(track_path)
        save_checkpoint(checkpoint_path, checkpoint)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    elif original_media:
        output_path = Path.cwd() / "output_uzbek.mp4"
    else:
        output_path = Path.cwd() / "output_uzbek.wav"

    if original_media:
        final_path = mux_with_video(original_media, track_path, output_path, ffmpeg=ffmpeg)
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(track_path, output_path)
        final_path = output_path

    checkpoint["output"] = str(final_path)
    checkpoint["status"] = "completed"
    save_checkpoint(checkpoint_path, checkpoint)
    return final_path


def build_parser() -> argparse.ArgumentParser:
    """Build the public CLI parser."""

    parser = argparse.ArgumentParser(
        prog="uzbek-dubbing",
        description="Ingliz/rus video yoki audio faylini o‘zbekcha dublyaj qilish.",
    )
    parser.add_argument("--input", required=True, help="Lokal media fayl yoki YouTube URL")
    parser.add_argument("--voice", default="sardor", choices=["sardor", "madina"], help="Ovoz")
    parser.add_argument("--lang", default="auto", choices=["auto", "en", "ru"], help="Manba tili")
    parser.add_argument("--output", help="Yakuniy fayl yo‘li")
    parser.add_argument("--work-dir", help="Checkpoint va vaqtinchalik fayllar katalogi")
    parser.add_argument("--whisper-model", help="Whisper modeli: small, medium yoki large-v3")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"], help="Whisper qurilmasi")
    parser.add_argument("--env-file", help="Maxsus .env fayl yo‘li")
    return parser


def main() -> int:
    """CLI main function."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    args = build_parser().parse_args()
    try:
        result = run_pipeline(args)
    except KeyboardInterrupt:
        LOGGER.error("Jarayon foydalanuvchi tomonidan to‘xtatildi. Keyingi ishga tushirish checkpoint’dan davom etadi.")
        return 130
    except Exception as exc:
        LOGGER.error("Dublyaj muvaffaqiyatsiz: %s", exc)
        return 1
    LOGGER.info("Tayyor: %s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
