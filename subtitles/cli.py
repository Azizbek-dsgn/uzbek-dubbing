"""Create frame-safe Uzbek SRT captions from local audio or video."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import sys
import tempfile
import subprocess
from dataclasses import dataclass
from pathlib import Path

# ONNX Runtime 1.29+ telemetry can abort macOS during native shutdown.
# Local transcription needs no telemetry; opt out before runtime initialization.
os.environ['ORT_DISABLE_TELEMETRY'] = '1'


@dataclass(frozen=True)
class Word:
    start: float
    end: float
    text: str
    confidence: float | None = None


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("’", "'").replace("‘", "'")
                  .replace("ʻ", "'").replace("ʼ", "'")).strip()


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


def _boundary_cost(left: Word, right: Word) -> float:
    """Prefer phrase boundaries without cutting Uzbek helpers from their phrase."""
    a = re.sub(r"[^\w']", '', _clean(left.text).casefold())
    b = re.sub(r"[^\w']", '', _clean(right.text).casefold())
    unfinished = {'va', 'yoki', 'hamda', 'juda', 'eng', 'har', 'bu', 'shu', 'o‘sha',
                  'bir', 'hech', 'barcha', 'qanday', 'қандай', 'ва', 'ёки', 'жуда', 'энг', 'ҳар', 'бу', 'шу', 'бир'}
    attached = {'emas', 'edi', 'ekan', 'kerak', 'mumkin', 'uchun', 'bilan', 'kabi', 'sari', 'qadar',
                'bo‘ladi', "bo'ladi", 'bo‘ldi', "bo'ldi", 'эмас', 'эди', 'экан', 'керак', 'мумкин', 'учун', 'билан', 'каби'}
    cost = (18 if a in unfinished else 0) + (18 if b in attached else 0)
    if a.isdigit() and (b in {'ta', 'ming', 'million', 'yil', 'kun', 'soat', 'foiz', 'kg', 'km', 'та', 'минг', 'кун', 'фоиз'}):
        cost += 25
    if re.search(r'[,;:]$', _clean(left.text)):
        cost -= 7
    if b in {'lekin', 'ammo', 'chunki', 'shuning', 'agar', 'лекин', 'аммо', 'чунки', 'агар'}:
        cost -= 4
    return cost - min(8, max(0, right.start - left.end) * 10)


def _natural_layout(group: list[Word], width: int, target: int, max_lines: int) -> str | None:
    # A word count is a reading target. Allow two extra words to finish a phrase.
    n = len(group); cap = target + 2
    best = {(0, 0): (0.0, [])}
    for lines in range(max_lines):
        for start in range(n):
            state = best.get((lines, start))
            if state is None:
                continue
            for end in range(start + 1, min(n, start + cap) + 1):
                text = _join(group[start:end])
                if len(text) > width and end > start + 1:
                    break
                penalty = max(0, end - start - target) ** 2
                if end < n:
                    penalty += _boundary_cost(group[end-1], group[end]) + 8
                candidate = (state[0] + penalty, state[1] + [text])
                key = (lines+1, end)
                if key not in best or candidate[0] < best[key][0]:
                    best[key] = candidate
    complete = [best[(lines, n)] for lines in range(1, max_lines+1) if (lines, n) in best]
    return '\n'.join(min(complete, key=lambda value: value[0])[1]) if complete else None


def _natural_groups(words: list[Word], width: int, target: int, lines: int, duration: float) -> list[list[Word]]:
    n = len(words); best = [float('inf')] * (n+1); following = [n] * n; best[n] = 0
    cap = (target+2)*lines
    for start in range(n-1, -1, -1):
        for end in range(start+1, min(n, start+cap)+1):
            if end > start+1 and words[end-1].end - words[start].start > duration:
                break
            if _natural_layout(words[start:end], width, target, lines) is None:
                continue
            count = end - start
            cost = 4 + max(0, count-target*lines)**2 * .5 + (8 if count == 1 and n > 1 else 0)
            if end < n:
                cost += _boundary_cost(words[end-1], words[end])
            if cost + best[end] <= best[start]:
                best[start] = cost + best[end]; following[start] = end
    result = []; start = 0
    while start < n:
        end = following[start]; result.append(words[start:end]); start = end
    return result


def make_cues(
    words: list[Word], fps: float = 25.0, max_chars: int = 42,
    max_duration: float = 5.0, gap: float = 0.65,
    max_lines: int = 2, words_per_line: int = 4,
    split_sentences: bool = True, split_commas: bool = False,
    split_pauses: bool = True, start_pad: float = 0.0,
    end_pad: float = 0.0, min_duration: float = 0.8,
    natural: bool = True,
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
                    (not natural and word.end - current[0].start > max_duration) or
                    (not natural and len(layout.splitlines()) > max_lines) or
                    (split_sentences and re.search(r"[.!?…]$", _clean(previous.text))) or
                    (split_commas and re.search(r"[,;:]$", _clean(previous.text)))):
                groups.append(current)
                current = []
        current.append(word)
    if current:
        groups.append(current)

    if natural:
        groups = [part for group in groups for part in _natural_groups(group, max_chars, words_per_line, max_lines, max_duration)]

    result: list[Cue] = []
    frame = 1.0 / fps
    # Distinct captions cannot begin within the same output frame. Keep all
    # words by merging those groups instead of drifting every later cue.
    packed: list[list[Word]] = []
    for group in groups:
        start_frame = math.floor(max(0.0, group[0].start - start_pad) * fps)
        if packed and start_frame <= math.floor(max(0.0, packed[-1][0].start - start_pad) * fps):
            packed[-1].extend(group)
        else:
            packed.append(group)
    groups = packed
    for i, group in enumerate(groups):
        start = max(0.0, math.floor(max(0.0, group[0].start - start_pad) * fps) / fps)
        if result:
            start = max(start, result[-1].end)
        end = max(math.ceil((group[-1].end + end_pad) * fps) / fps,
                  start + math.ceil(min_duration * fps) / fps)
        if i + 1 < len(groups):
            next_start = math.floor(max(0.0, groups[i + 1][0].start - start_pad) * fps) / fps
            end = min(end, next_start)
        end = max(start + frame, end)
        # If a same-frame merge exceeded the layout limit, allow the minimum
        # extra words needed to preserve timing and avoid losing speech.
        effective_words = max(words_per_line, math.ceil(len(group) / max_lines))
        text = (_natural_layout(group, max_chars, words_per_line, max_lines) if natural else None) or _wrap(_join(group), max_chars, effective_words)
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


def apply_replacements(words: list[Word], rules: list[str]) -> list[Word]:
    """Replace one recognized word at a time without changing its timestamps."""
    mapping: dict[str, str] = {}
    for rule in rules:
        separator = "=>" if "=>" in rule else "="
        if separator not in rule:
            raise ValueError(f"Lug‘at qatori noto‘g‘ri: {rule}")
        source, target = (_clean(part) for part in rule.split(separator, 1))
        if not source or not target or any(c.isspace() for c in source + target):
            raise ValueError(f"Lug‘atda faqat bitta so‘zni almashtiring: {rule}")
        mapping[source.casefold()] = target
    result: list[Word] = []
    for word in words:
        match = re.match(r"^([^\w'\-]*)([\w'\-]+)([^\w'\-]*)$", _clean(word.text), re.UNICODE)
        if not match:
            result.append(word)
            continue
        original = match.group(2)
        replacement = mapping.get(original.casefold())
        if replacement is None:
            result.append(word)
            continue
        if original.isupper():
            replacement = replacement.upper()
        elif original[:1].isupper():
            replacement = replacement[:1].upper() + replacement[1:]
        result.append(Word(word.start, word.end, match.group(1) + replacement + match.group(3), word.confidence))
    return result


def transcribe(path: Path, model_name: str, device: str, progress=None, *, preserve_repeats=False) -> list[Word]:
    if model_name == "zafar-fastconformer":
        if __package__:
            from .fastconformer import transcribe as fastconformer_transcribe
        else:
            from fastconformer import transcribe as fastconformer_transcribe
        checkpoint = (Path(__file__).resolve().parent.parent / "models" /
                      "zafar-fastconformer" / "uzbek_stt_v12.nemo")
        return [Word(start, end, value) for start, end, value in
                fastconformer_transcribe(path, checkpoint, device, progress)]
    if model_name == "gigaam-uzbek":
        if __package__:
            from .gigaam import transcribe as gigaam_transcribe
        else:
            from gigaam import transcribe as gigaam_transcribe
        root = Path(__file__).resolve().parent.parent / "models"
        rows = gigaam_transcribe(path, root / "gigaam-base-large",
                                 root / "gigaam-uzbek" / "checkpoints" / "large_full_600m" / "best.pt",
                                 device, progress=progress)
        return [Word(max(0.0, start), max(start + 0.01, end), text)
                for start, end, text in rows]
    try:
        if sys.platform == "darwin" and platform.machine().lower() == "x86_64":
            # Initialize PyTorch's native libraries first when both ASR engines
            # are installed (including comparisons that start with NavAI).
            try:
                import torch
            except ImportError:
                pass
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("faster-whisper topilmadi; subtitles/requirements.txt ni o'rnating") from exc
    if device == "auto":
        # The one-command installer includes the CPU runtime. An NVIDIA
        # driver alone does not provide the CUDA/cuDNN libraries Whisper needs.
        device = "cpu"
    local_model = Path(__file__).resolve().parent.parent / "models" / model_name
    if model_name.startswith("navai-") and not (local_model / "model.bin").is_file():
        raise RuntimeError(f"NavAI modeli o'rnatilmagan: models/{model_name}/model.bin")
    model_ref = str(local_model) if (local_model / "model.bin").is_file() else model_name
    model = WhisperModel(model_ref, device=device,
                         compute_type="float16" if device == "cuda" else "int8")
    segments, info = model.transcribe(
        str(path), language="uz", task="transcribe", beam_size=5,
        temperature=0, repetition_penalty=1.0 if preserve_repeats else 1.1,
        no_repeat_ngram_size=0 if preserve_repeats else 4,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 300, "threshold": 0.35},
        word_timestamps=True, condition_on_previous_text=False,
    )
    words: list[Word] = []
    for segment in segments:
        if progress and info.duration:
            progress(min(int(float(segment.end) / info.duration * 100), 100), 100)
        if not _reliable_segment(segment):
            continue
        if segment.words:
            for word in segment.words:
                if word.start is not None and word.end is not None:
                    words.append(Word(float(word.start), float(word.end), word.word,
                                      float(word.probability) if word.probability is not None else None))
        elif segment.text.strip():
            words.append(Word(float(segment.start), float(segment.end), segment.text))
    return words


def to_vtt(cues: list[Cue]) -> str:
    return "WEBVTT\n\n" + "".join(
        f"{_stamp(c.start).replace(',', '.')} --> {_stamp(c.end).replace(',', '.')}\n{c.text}\n\n"
        for c in cues)


def to_ass(cues: list[Cue], speakers: list[str | None] | None = None) -> str:
    header = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n"
              "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
              "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
              "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
              "MarginR, MarginV, Encoding\n"
              "Style: Default,Arial,56,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
              "0,0,0,0,100,100,0,0,1,2,1,2,80,80,75,1\n\n"
              "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    def stamp(t: float) -> str:
        hundredths = round(t * 100)
        h, rest = divmod(hundredths, 360000)
        m, rest = divmod(rest, 6000)
        s, cs = divmod(rest, 100)
        return f"{h}:{m:02}:{s:02}.{cs:02}"
    return header + "".join(
        f"Dialogue: 0,{stamp(c.start)},{stamp(c.end)},Default,{re.sub(r'[^A-Za-z0-9_-]', '', (speakers[i] or '')) if speakers else ''},0,0,0,,"
        + c.text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")
        + "\n" for i, c in enumerate(cues))


_LATIN_TO_CYRILLIC = {
    "sh": "ш", "ch": "ч", "ng": "нг", "yo": "ё", "yu": "ю", "ya": "я",
    "o'": "ў", "g'": "ғ", "a": "а", "b": "б", "d": "д", "e": "е",
    "f": "ф", "g": "г", "h": "ҳ", "i": "и", "j": "ж", "k": "к",
    "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "қ",
    "r": "р", "s": "с", "t": "т", "u": "у", "v": "в", "x": "х",
    "y": "й", "z": "з", "'": "ъ",
}


def to_cyrillic(text: str) -> str:
    """Practical Uzbek transliteration; proper names may need manual review."""
    source = _clean(text)
    out: list[str] = []
    index = 0
    while index < len(source):
        token = next((source[index:index + size] for size in (2, 1)
                      if source[index:index + size].lower() in _LATIN_TO_CYRILLIC), None)
        if token is None:
            out.append(source[index]); index += 1; continue
        mapped = _LATIN_TO_CYRILLIC[token.lower()]
        out.append(mapped.upper() if token[0].isupper() else mapped)
        index += len(token)
    return "".join(out)


def diarize(path: Path, model_dir: Path, count: int | None = None) -> list[dict]:
    """Run the installed local pyannote pipeline and return speaker turns."""
    if not (model_dir / "config.yaml").is_file():
        raise RuntimeError("So‘zlovchilar modeli o‘rnatilmagan")
    cache = model_dir.parent / ".mpl-cache"
    cache.mkdir(exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache))
    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise RuntimeError("So‘zlovchilar uchun pyannote.audio o‘rnatilmagan") from exc
    import imageio_ffmpeg
    import soundfile as sf
    import torch
    pipeline = Pipeline.from_pretrained(str(model_dir))
    with tempfile.TemporaryDirectory() as directory:
        wav = Path(directory) / "speech.wav"
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-y", "-loglevel", "error",
                        "-i", str(path), "-ac", "1", "-ar", "16000", str(wav)], check=True)
        signal, rate = sf.read(wav, dtype="float32")
        waveform = torch.from_numpy(signal).unsqueeze(0)
        result = pipeline({"waveform": waveform, "sample_rate": rate},
                          **({"num_speakers": count} if count else {}))
    annotation = getattr(result, "speaker_diarization", result)
    return [{"start": round(float(turn.start), 3), "end": round(float(turn.end), 3),
             "speaker": str(label)} for turn, _, label in annotation.itertracks(yield_label=True)]


def cue_speaker(cue: Cue, turns: list[dict]) -> str | None:
    scores: dict[str, float] = {}
    for turn in turns:
        overlap = max(0.0, min(cue.end, turn["end"]) - max(cue.start, turn["start"]))
        if overlap:
            scores[turn["speaker"]] = scores.get(turn["speaker"], 0) + overlap
    return max(scores, key=scores.get) if scores else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline o'zbekcha SRT subtitr yaratuvchi")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default="gigaam-uzbek", choices=["large-v3", "navai-medium", "gigaam-uzbek"])
    parser.add_argument("--compare-model", choices=["large-v3", "navai-medium", "gigaam-uzbek"])
    parser.add_argument("--script", choices=["latin", "cyrillic"], default="latin")
    parser.add_argument("--export-vtt", action="store_true")
    parser.add_argument("--export-ass", action="store_true")
    parser.add_argument("--word-mode", action="store_true")
    parser.add_argument("--fixed-word-breaks", action="store_true", help="Use strict word-count caption limits instead of natural phrase boundaries")
    parser.add_argument("--speakers", action="store_true")
    parser.add_argument("--num-speakers", type=int, choices=[2, 3, 4])
    parser.add_argument("--start-seconds", type=float, default=0)
    parser.add_argument("--end-seconds", type=float)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda", "mps"])
    parser.add_argument("--fps", type=float, default=25.0)
    parser.add_argument("--max-chars", type=int, default=42)
    parser.add_argument("--lines", type=int, default=2)
    parser.add_argument("--words-per-line", type=int, default=4)
    parser.add_argument("--max-duration", type=float, default=5.0)
    parser.add_argument("--pause", type=float, default=0.65)
    parser.add_argument("--no-sentence-split", action="store_true")
    parser.add_argument("--no-sentence-restore", action="store_true")
    parser.add_argument("--literary", action="store_true",
                        help="Keng tarqalgan so‘zlashuv shakllarini adabiy yozuvga yaqinlashtirish")
    parser.add_argument("--split-commas", action="store_true")
    parser.add_argument("--no-pause-split", action="store_true")
    parser.add_argument("--start-pad-ms", type=int, default=0)
    parser.add_argument("--end-pad-ms", type=int, default=0)
    parser.add_argument("--min-cue-duration", type=float, default=0.8)
    parser.add_argument("--replace", action="append", default=[], metavar="XATO=TOGRI")
    args = parser.parse_args(argv)
    try:
        if not args.input.is_file():
            raise FileNotFoundError(f"Media topilmadi: {args.input}")
        apply_replacements([], args.replace)
        def report(done: int, total: int) -> None:
            print(f"UZPROGRESS {done}/{total}", file=sys.stderr, flush=True)
        if args.start_seconds < 0 or (args.end_seconds is not None and
                                      args.end_seconds <= args.start_seconds):
            raise ValueError("Qayta tanish vaqti noto'g'ri")
        source = args.input
        offset = 0.0
        scratch = tempfile.TemporaryDirectory()
        try:
            if args.start_seconds or args.end_seconds is not None:
                try:
                    import imageio_ffmpeg
                    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
                except ImportError as exc:
                    raise RuntimeError("Oraliq uchun imageio-ffmpeg kerak") from exc
                source = Path(scratch.name) / "selection.wav"
                command = [ffmpeg, "-nostdin", "-y", "-loglevel", "error", "-ss",
                           str(args.start_seconds), "-i", str(args.input)]
                if args.end_seconds is not None:
                    command.extend(["-t", str(args.end_seconds - args.start_seconds)])
                command.extend(["-ac", "1", "-ar", "16000", str(source)])
                subprocess.run(command, check=True)
                offset = args.start_seconds
            words = transcribe(source, args.model, args.device, report)
            if args.literary:
                if __package__:
                    from .sentences import standardize_literary
                else:
                    from sentences import standardize_literary
                words = standardize_literary(words)
            words = apply_replacements(words, args.replace)
            words = [Word(max(offset, w.start + offset),
                          max(offset + 0.01, w.end + offset, w.start + offset + 0.01),
                          w.text, w.confidence) for w in words]
            comparison = None
            if args.compare_model and args.compare_model != args.model:
                alternative = transcribe(source, args.compare_model, args.device, report)
                if args.literary:
                    alternative = standardize_literary(alternative)
                alternative = apply_replacements(alternative, args.replace)
                comparison = [{"start": round(w.start + offset, 3), "end": round(w.end + offset, 3),
                               "text": w.text, "confidence": w.confidence} for w in alternative]
            turns = diarize(source, Path(__file__).resolve().parent.parent / "models" / "speaker-diarization",
                            args.num_speakers) if args.speakers else []
            for turn in turns:
                turn["start"] = round(turn["start"] + offset, 3)
                turn["end"] = round(turn["end"] + offset, 3)
        finally:
            scratch.cleanup()
        if not args.no_sentence_restore:
            if __package__:
                from .sentences import local_corrector, restore_sentences
            else:
                from sentences import local_corrector, restore_sentences
            try:
                correct = local_corrector(Path(__file__).resolve().parent.parent)
            except Exception as exc:
                print(f"Matn modeli yuklanmadi, oddiy gap bo‘linishi ishlatiladi: {exc}", file=sys.stderr)
                correct = None
            words = restore_sentences(words, correct, strong_pause=max(0.8, args.pause + 0.2))
        if args.script == "cyrillic":
            words = [Word(w.start, w.end, to_cyrillic(w.text), w.confidence) for w in words]
            if comparison is not None:
                for item in comparison:
                    item["text"] = to_cyrillic(item["text"])
        cues = make_cues(words, fps=args.fps, max_chars=args.max_chars,
                         max_duration=args.max_duration, gap=args.pause,
                         max_lines=1 if args.word_mode else args.lines,
                         words_per_line=1 if args.word_mode else args.words_per_line,
                         split_sentences=not args.no_sentence_split,
                         split_commas=args.split_commas,
                         split_pauses=not args.no_pause_split,
                         start_pad=args.start_pad_ms / 1000,
                         end_pad=args.end_pad_ms / 1000,
                         min_duration=0 if args.word_mode else args.min_cue_duration,
                         natural=not args.word_mode and not args.fixed_word_breaks)
        if not cues:
            raise RuntimeError("Nutq topilmadi")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(to_srt(cues), encoding="utf-8-sig")
        if args.export_vtt:
            args.output.with_suffix(".vtt").write_text(to_vtt(cues), encoding="utf-8")
        if args.export_ass:
            args.output.with_suffix(".ass").write_text(
                to_ass(cues, [cue_speaker(c, turns) for c in cues]), encoding="utf-8")
        metadata = {"model": args.model, "words": [
            {"start": round(w.start, 3), "end": round(w.end, 3), "text": w.text,
             "confidence": w.confidence} for w in words], "comparison_model": args.compare_model,
            "comparison_words": comparison,
            "speaker_turns": turns,
            "cues": [{"start": c.start, "end": c.end, "text": c.text,
                      "speaker": cue_speaker(c, turns)} for c in cues]}
        args.output.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"output": str(args.output.resolve()), "cues": len(cues)}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
