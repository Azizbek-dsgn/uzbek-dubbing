"""Create one set of Uzbek subtitle files per media file in a folder."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .cli import main as transcribe_one
except ImportError:
    from cli import main as transcribe_one


MEDIA = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".mp4", ".mov", ".mkv"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Papkadagi media fayllaridan SRT yaratish")
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", default="gigaam-uzbek")
    parser.add_argument("--script", choices=["latin", "cyrillic"], default="latin")
    parser.add_argument("--fps", type=float, default=25)
    parser.add_argument("--export-vtt", action="store_true")
    parser.add_argument("--export-ass", action="store_true")
    parser.add_argument("--word-mode", action="store_true")
    parser.add_argument("--speakers", action="store_true")
    parser.add_argument("--num-speakers", type=int, choices=[2, 3, 4])
    args = parser.parse_args()
    if not args.input_dir.is_dir():
        parser.error("Kirish papkasi topilmadi")
    files = sorted(p for p in args.input_dir.iterdir() if p.is_file() and p.suffix.lower() in MEDIA)
    if not files:
        parser.error("Papkada media fayl topilmadi")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    failed = 0
    for index, media in enumerate(files, 1):
        print(f"UZBATCH {index}/{len(files)} {media.name}", flush=True)
        argv = ["--input", str(media), "--output", str(args.output_dir / (media.stem + ".uz.srt")),
                "--model", args.model, "--script", args.script, "--fps", str(args.fps)]
        for flag in ("export_vtt", "export_ass", "word_mode", "speakers"):
            if getattr(args, flag):
                argv.append("--" + flag.replace("_", "-"))
        if args.num_speakers:
            argv.extend(["--num-speakers", str(args.num_speakers)])
        failed += transcribe_one(argv) != 0
    print(f"UZBATCH_DONE {len(files) - failed}/{len(files)}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
