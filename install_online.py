"""Install UzScribe from a GitHub checkout, downloading the Uzbek model on first use."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

from install import destinations, install


ROOT = Path(__file__).resolve().parent
MODEL_REPO = "navai-uz/whisper-small-uzbek"
MODEL_REVISION = "017136a1a50b2497ba94edeaac9fbb0a6c773c22"
CONVERTER_DEPENDENCIES = (
    "transformers>=4.47,<6",
    "torch>=2.3,<3",
    "huggingface_hub>=0.34,<2",
)
CONVERT = r"""
import os
import shutil
import sys
from pathlib import Path

repo, revision, temporary = sys.argv[1:]
os.environ.setdefault("HF_HOME", str(Path(temporary) / "hf-cache"))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from huggingface_hub import snapshot_download
from ctranslate2.converters import TransformersConverter
from transformers import AutoTokenizer

source = Path(temporary) / "source"
output = Path(temporary) / "converted"
snapshot_download(repo_id=repo, revision=revision, local_dir=source,
                  allow_patterns=["*.json", "*.safetensors", "merges.txt", "LICENSE", "NOTICE"])
if not (source / "model.safetensors").is_file():
    raise RuntimeError("NavAI model vaznlari yuklanmadi")
converter = TransformersConverter(str(source),
                                  copy_files=["preprocessor_config.json"])
converter.convert(str(output), quantization="int8")
AutoTokenizer.from_pretrained(str(source), use_fast=True).save_pretrained(str(output))
for name in ("LICENSE", "NOTICE"):
    shutil.copy2(source / name, output / name)
if not (output / "model.bin").is_file() or not (output / "tokenizer.json").is_file():
    raise RuntimeError("CTranslate2 modeli yaratilmadi")
"""


def _python_for(runtime: Path, system: str) -> Path:
    return runtime / ".venv" / ("Scripts/python.exe" if system == "win32" else "bin/python")


def _prepare_environment(runtime: Path, system: str, *, convert: bool) -> Path:
    python = _python_for(runtime, system)
    if not python.is_file():
        venv.EnvBuilder(with_pip=True).create(runtime / ".venv")
    subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check",
                    "-r", str(ROOT / "subtitles" / "requirements-release.txt")], check=True)
    if convert:
        subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check",
                        *CONVERTER_DEPENDENCIES], check=True)
    return python


def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub’dan UzScribe o‘rnatish")
    parser.add_argument("--model-dir", type=Path,
                        help="Mavjud CTranslate2 NavAI small modeli; yuklashni o‘tkazib yuboradi")
    args = parser.parse_args()
    if not (3, 10) <= sys.version_info[:2] < (3, 13):
        parser.error("Python 3.10, 3.11 yoki 3.12 kerak")
    try:
        runtime, _ = destinations(sys.platform, Path.home(), dict(os.environ))
        existing = runtime / "models" / "navai-small"
        model = args.model_dir or (existing if (existing / "model.bin").is_file() else None)
        python = _prepare_environment(runtime, sys.platform, convert=model is None)
        if model is None:
            with tempfile.TemporaryDirectory(prefix="uzscribe-model-") as temporary:
                print("NavAI o‘zbekcha modeli yuklanmoqda va tayyorlanmoqda…", flush=True)
                subprocess.run([str(python), "-c", CONVERT, MODEL_REPO,
                                MODEL_REVISION, temporary], check=True)
                install(ROOT, sys.platform, Path.home(), dict(os.environ),
                        developer=True, skip_dependencies=True,
                        model_source=Path(temporary) / "converted")
        else:
            install(ROOT, sys.platform, Path.home(), dict(os.environ),
                    developer=True, skip_dependencies=True, model_source=model)
        subprocess.run([str(python), "-c", "import faster_whisper, imageio_ffmpeg"], check=True)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"UzScribe o‘rnatilmadi: {exc}", file=sys.stderr)
        return 1
    print("UzScribe o‘rnatildi. Premiere Pro yoki After Effects’ni qayta oching.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
