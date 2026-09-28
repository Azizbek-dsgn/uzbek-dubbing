"""Create frame-safe Uzbek SRT captions from local audio or video."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Word:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("’", "'").replace("ʻ", "'")).strip()


def _join(words: list[Word]) -> str:
    text = ""
    for word in words:
        part = _clean(word.text)
        if not part:
            continue
        if part[0] in ",.!?:;)]}" and text:
            text += part
        elif part[0] in "'" and text and word.text[:1] != " ":
            text += part
        else:
            text += (" " if text else "") + part
    return text


def _wrap(text: str, width: int) -> str:
    lines = [""]
    for word in text.split():
        if lines[-1] and len(lines[-1]) + len(word) + 1 > width and len(lines) < 2:
            lines.append(word)
        else:
            lines[-1] += (" " if lines[-1] else "") + word
    return "\n".join(lines)


def make_cues(
    words: list[Word], fps: float = 25.0, max_chars: int = 42,
    max_duration: float = 5.0, gap: float = 0.65,
) -> list[Cue]:
    """Group words at pauses, punctuation and readable line/duration limits."""
    if fps <= 0 or max_chars < 8 or max_duration <= 0:
        raise ValueError("fps, max_chars va max_duration musbat bo'lishi kerak")
    ordered = sorted((w for w in words if _clean(w.text) and w.end > w.start), key=lambda w: w.start)
    groups: list[list[Word]] = []
    current: list[Word] = []
    for word in ordered:
        if current:
            previous = current[-1]
            proposed = _join(current + [word])
            if (word.start - previous.end > gap or
                    word.end - current[0].start > max_duration or
                    len(proposed) > 2 * max_chars or
                    (re.search(r"[.!?]$", _clean(previous.text)) and
                     word.start - previous.end >= 0.12)):
                groups.append(current)
                current = []
        current.append(word)
    if current:
        groups.append(current)

    result: list[Cue] = []
    frame = 1.0 / fps
    for i, group in enumerate(groups):
        start = max(0.0, math.floor(group[0].start * fps) / fps)
        if result:
            start = max(start, result[-1].end + frame)
        end = max(math.ceil(group[-1].end * fps) / fps,
                  start + math.ceil(0.8 * fps) / fps)
        if i + 1 < len(groups):
            next_start = math.floor(groups[i + 1][0].start * fps) / fps
            end = min(end, next_start - frame)
        end = max(start + frame, end)
        text = _wrap(_join(group), max_chars)
        result.append(Cue(round(start, 3), round(end, 3), text))
    return result


def _stamp(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def to_srt(cues: list[Cue]) -> str:
    return "".join(
        f"{i}\n{_stamp(cue.start)} --> {_stamp(cue.end)}\n{cue.text}\n\n"
        for i, cue in enumerate(cues, 1)
    )


def transcribe(path: Path, model_name: str, device: str) -> list[Word]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("faster-whisper topilmadi; subtitles/requirements.txt ni o'rnating") from exc
    if device == "auto":
        try:
            import subprocess
            probe = subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=3)
            device = "cuda" if probe.returncode == 0 and probe.stdout else "cpu"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            device = "cpu"
    model = WhisperModel(model_name, device=device,
                         compute_type="float16" if device == "cuda" else "int8")
    segments, _ = model.transcribe(
        str(path), language="uz", beam_size=5, vad_filter=True,
        word_timestamps=True, condition_on_previous_text=False,
        initial_prompt="O'zbek tilidagi nutq. O‘zbekiston, Toshkent, qo‘shimcha, bugun.",
    )
    words: list[Word] = []
    for segment in segments:
        if segment.words:
            for word in segment.words:
                if word.start is not None and word.end is not None:
                    words.append(Word(float(word.start), float(word.end), word.word))
        elif segment.text.strip():
            words.append(Word(float(segment.start), float(segment.end), segment.text))
    return words


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline o'zbekcha SRT subtitr yaratuvchi")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default="large-v3", choices=["small", "medium", "large-v3"])
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--fps", type=float, default=25.0)
    parser.add_argument("--max-chars", type=int, default=42)
    args = parser.parse_args(argv)
    try:
        if not args.input.is_file():
            raise FileNotFoundError(f"Media topilmadi: {args.input}")
        words = transcribe(args.input, args.model, args.device)
        cues = make_cues(words, fps=args.fps, max_chars=args.max_chars)
        if not cues:
            raise RuntimeError("Nutq topilmadi")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(to_srt(cues), encoding="utf-8-sig")
        print(json.dumps({"output": str(args.output.resolve()), "cues": len(cues)}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
