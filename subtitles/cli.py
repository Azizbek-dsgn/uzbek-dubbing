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
        elif text and part[0] in "'-’" and word.text[:1] and not word.text[:1].isspace():
            text += part
        else:
            text += (" " if text else "") + part
    return text


def _wrap(text: str, width: int, words_per_line: int) -> str:
    lines = [""]
    count = 0
    for word in text.split():
        if lines[-1] and (len(lines[-1]) + len(word) + 1 > width or count >= words_per_line):
            lines.append(word)
            count = 1
        else:
            lines[-1] += (" " if lines[-1] else "") + word
            count += 1
    return "\n".join(lines)


def make_cues(
    words: list[Word], fps: float = 25.0, max_chars: int = 42,
    max_duration: float = 5.0, gap: float = 0.65,
    max_lines: int = 2, words_per_line: int = 4,
    split_sentences: bool = True, split_commas: bool = False,
    split_pauses: bool = True, start_pad: float = 0.0,
    end_pad: float = 0.0, min_duration: float = 0.8,
) -> list[Cue]:
    """Group words at pauses, punctuation and readable line/duration limits."""
    if (fps <= 0 or max_chars < 8 or max_duration <= 0 or
            not 1 <= max_lines <= 3 or not 1 <= words_per_line <= 8 or
            not 0 <= start_pad <= 0.5 or not 0 <= end_pad <= 0.5 or
            not 0 <= min_duration <= 3):
        raise ValueError("FPS va subtitr o'lchamlari noto'g'ri")
    ordered = sorted((w for w in words if _clean(w.text) and w.end > w.start), key=lambda w: w.start)
    groups: list[list[Word]] = []
    current: list[Word] = []
    for word in ordered:
        if current:
            previous = current[-1]
            proposed = _join(current + [word])
            layout = _wrap(proposed, max_chars, words_per_line)
            if ((split_pauses and word.start - previous.end > gap) or
                    word.end - current[0].start > max_duration or
                    len(layout.splitlines()) > max_lines or
                    (split_sentences and re.search(r"[.!?…]$", _clean(previous.text))) or
                    (split_commas and re.search(r"[,;:]$", _clean(previous.text)))):
                groups.append(current)
                current = []
        current.append(word)
    if current:
        groups.append(current)

    result: list[Cue] = []
    frame = 1.0 / fps
    for i, group in enumerate(groups):
        start = max(0.0, math.floor(max(0.0, group[0].start - start_pad) * fps) / fps)
        if result:
            start = max(start, result[-1].end + frame)
        end = max(math.ceil((group[-1].end + end_pad) * fps) / fps,
                  start + math.ceil(min_duration * fps) / fps)
        if i + 1 < len(groups):
            next_start = math.floor(max(0.0, groups[i + 1][0].start - start_pad) * fps) / fps
            end = min(end, next_start - frame)
        end = max(start + frame, end)
        text = _wrap(_join(group), max_chars, words_per_line)
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


def _reliable_segment(segment: object) -> bool:
    """Discard only segments whose text and every word have very low confidence."""
    if float(segment.avg_logprob) >= -1.0:
        return True
    return any(float(word.probability) >= 0.2 for word in (segment.words or []))


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
    local_model = Path(__file__).resolve().parent.parent / "models" / model_name
    if model_name == "navai-medium" and not (local_model / "model.bin").is_file():
        raise RuntimeError("NavAI o'zbekcha modeli o'rnatilmagan; models/navai-medium/model.bin topilmadi")
    model_ref = str(local_model) if (local_model / "model.bin").is_file() else model_name
    model = WhisperModel(model_ref, device=device,
                         compute_type="float16" if device == "cuda" else "int8")
    segments, _ = model.transcribe(
        str(path), language="uz", task="transcribe", beam_size=5,
        temperature=0, repetition_penalty=1.1, no_repeat_ngram_size=4,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 300, "threshold": 0.35},
        word_timestamps=True, condition_on_previous_text=False,
    )
    words: list[Word] = []
    for segment in segments:
        if not _reliable_segment(segment):
            continue
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
    parser.add_argument("--model", default="large-v3", choices=["small", "medium", "large-v3", "navai-medium"])
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--fps", type=float, default=25.0)
    parser.add_argument("--max-chars", type=int, default=42)
    parser.add_argument("--lines", type=int, default=2)
    parser.add_argument("--words-per-line", type=int, default=4)
    parser.add_argument("--max-duration", type=float, default=5.0)
    parser.add_argument("--pause", type=float, default=0.65)
    parser.add_argument("--no-sentence-split", action="store_true")
    parser.add_argument("--split-commas", action="store_true")
    parser.add_argument("--no-pause-split", action="store_true")
    parser.add_argument("--start-pad-ms", type=int, default=0)
    parser.add_argument("--end-pad-ms", type=int, default=0)
    parser.add_argument("--min-cue-duration", type=float, default=0.8)
    args = parser.parse_args(argv)
    try:
        if not args.input.is_file():
            raise FileNotFoundError(f"Media topilmadi: {args.input}")
        words = transcribe(args.input, args.model, args.device)
        cues = make_cues(words, fps=args.fps, max_chars=args.max_chars,
                         max_duration=args.max_duration, gap=args.pause,
                         max_lines=args.lines, words_per_line=args.words_per_line,
                         split_sentences=not args.no_sentence_split,
                         split_commas=args.split_commas,
                         split_pauses=not args.no_pause_split,
                         start_pad=args.start_pad_ms / 1000,
                         end_pad=args.end_pad_ms / 1000,
                         min_duration=args.min_cue_duration)
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
