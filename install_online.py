"""Install UzScribe from source, preparing Python, NavAI and GigaAM."""

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

DOWNLOAD_GIGAAM = r"""
import sys
from pathlib import Path
from huggingface_hub import hf_hub_download

runtime = Path(sys.argv[1])
base = runtime / "models" / "gigaam-base-large"
uzbek = runtime / "models" / "gigaam-uzbek"
for name in ("config.json", "modeling_gigaam.py"):
    if not (base / name).is_file():
        hf_hub_download("ai-sage/GigaAM-Multilingual", name,
                        revision="large_ctc", local_dir=base)
checkpoint = uzbek / "checkpoints" / "large_full_600m" / "best.pt"
if not checkpoint.is_file() or checkpoint.stat().st_size < 100_000_000:
    hf_hub_download("rustam1221/uzbek-asr-gigaam",
                    "checkpoints/large_full_600m/best.pt", local_dir=uzbek)
if not all((base / name).is_file() for name in ("config.json", "modeling_gigaam.py")):
    raise RuntimeError("GigaAM asosiy fayllari yuklanmadi")
if not checkpoint.is_file() or checkpoint.stat().st_size < 100_000_000:
    raise RuntimeError("GigaAM Uzbek 600M modeli yuklanmadi")
"""


def _python_for(runtime: Path, system: str) -> Path:
    return runtime / ".venv" / ("Scripts/python.exe" if system == "win32" else "bin/python")


def _navai_ready(directory: Path) -> bool:
    return all((directory / name).is_file()
               for name in ("model.bin", "config.json", "tokenizer.json"))


def _prepare_environment(runtime: Path, system: str, *, convert: bool,
                         uv: Path | None = None) -> Path:
    python = _python_for(runtime, system)
    if not python.is_file():
        if uv:
            subprocess.run([str(uv), "venv", "--python", sys.executable,
                            str(runtime / ".venv")], check=True)
        else:
            venv.EnvBuilder(with_pip=True).create(runtime / ".venv")
    if uv:
        base_command = [str(uv), "pip", "install", "--python", str(python)]
    else:
        base_command = [str(python), "-m", "pip", "install", "--disable-pip-version-check"]
    subprocess.run([*base_command, "-r",
                    str(ROOT / "subtitles" / "requirements-release.txt")], check=True)
    if convert:
        subprocess.run([*base_command, *CONVERTER_DEPENDENCIES], check=True)
    return python


def _install_gigaam(runtime: Path, python: Path, uv: Path | None) -> None:
    if uv:
        command = [str(uv), "pip", "install", "--python", str(python)]
    else:
        command = [str(python), "-m", "pip", "install", "--disable-pip-version-check"]
    subprocess.run([*command, "-r", str(ROOT / "subtitles" / "requirements-gigaam.txt"),
                    "huggingface_hub>=0.34,<2"], check=True)
    subprocess.run([str(python), "-c", "import torch, torchaudio, hydra, soundfile, transformers, huggingface_hub"],
                   check=True)
    print("GigaAM Uzbek 600M yuklanmoqda (taxminan 2.3 GB)…", flush=True)
    subprocess.run([str(python), "-c", DOWNLOAD_GIGAAM, str(runtime)], check=True)


def _verify_installation(runtime: Path, panel: Path, python: Path) -> None:
    if not python.is_file():
        raise RuntimeError("UzScribe Python muhiti topilmadi")
    if not _navai_ready(runtime / "models" / "navai-small"):
        raise RuntimeError("NavAI modeli to‘liq o‘rnatilmadi")
    base = runtime / "models" / "gigaam-base-large"
    if not all((base / name).is_file() for name in ("config.json", "modeling_gigaam.py")):
        raise RuntimeError("GigaAM asosiy fayllari to‘liq o‘rnatilmadi")
    checkpoint = (runtime / "models" / "gigaam-uzbek" / "checkpoints" /
                  "large_full_600m" / "best.pt")
    if not checkpoint.is_file() or checkpoint.stat().st_size < 100_000_000:
        raise RuntimeError("GigaAM Uzbek 600M checkpointi to‘liq o‘rnatilmadi")
    for name in ("CSXS/manifest.xml", "index.html", "panel.js",
                 "assets/uzscribe-logo.jpg"):
        if not (panel / name).is_file():
            raise RuntimeError(f"Adobe panel fayli yetishmayapti: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub’dan UzScribe o‘rnatish")
    parser.add_argument("--model-dir", type=Path,
                        help="Mavjud CTranslate2 NavAI small modeli; yuklashni o‘tkazib yuboradi")
    args = parser.parse_args()
    if not (3, 10) <= sys.version_info[:2] < (3, 13):
        parser.error("Python 3.10, 3.11 yoki 3.12 kerak")
    try:
        runtime, panel = destinations(sys.platform, Path.home(), dict(os.environ))
        existing = runtime / "models" / "navai-small"
        if args.model_dir and not _navai_ready(args.model_dir):
            raise FileNotFoundError(f"NavAI modeli to‘liq emas: {args.model_dir}")
        model = args.model_dir or (existing if _navai_ready(existing) else None)
        uv = Path(os.environ["UZSCRIBE_UV_BIN"]) if os.environ.get("UZSCRIBE_UV_BIN") else None
        python = _prepare_environment(runtime, sys.platform, convert=model is None, uv=uv)
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
        _install_gigaam(runtime, python, uv)
        _verify_installation(runtime, panel, python)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"UzScribe o‘rnatilmadi: {exc}", file=sys.stderr)
        return 1
    print("UzScribe o‘rnatildi. Premiere Pro yoki After Effects’ni qayta oching.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
