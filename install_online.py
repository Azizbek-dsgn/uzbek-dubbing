"""Install UzScribe from source, preparing Python and strong offline speech models."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import uuid
import venv
from pathlib import Path

from install import destinations, install, _copy_panel, _enable_debug
from subtitles.model_assets import require_features


ROOT = Path(__file__).resolve().parent
MODEL_REPO = "Systran/faster-whisper-large-v3"
MODEL_REVISION = "edaa852ec7e145841d8ffdb056a99866b5f0a478"
CONVERTER_DEPENDENCIES = ("huggingface_hub>=0.34,<2",)
# Already converted, immutable model; no conversion toolchain is needed.
CONVERT = r"""
import os
import sys
from pathlib import Path
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from huggingface_hub import snapshot_download
repo, revision, temporary = sys.argv[1:]
output = Path(temporary) / "converted"
snapshot_download(repo_id=repo, revision=revision, local_dir=output,
                  allow_patterns=["model.bin", "config.json", "preprocessor_config.json",
                                  "tokenizer.json", "vocabulary.json"])
if not (output / "model.bin").is_file():
    raise RuntimeError("UzScribe Global modeli yuklanmadi")
"""

DOWNLOAD_GIGAAM = r"""
import hashlib
import os
import sys
from pathlib import Path
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from huggingface_hub import hf_hub_download

runtime = Path(sys.argv[1])
base = runtime / "models" / "gigaam-base-large"
uzbek = runtime / "models" / "gigaam-uzbek"
for name in ("config.json", "modeling_gigaam.py"):
    if not (base / name).is_file():
        hf_hub_download("ai-sage/GigaAM-Multilingual", name,
                        revision="3905cd51c3ed4e88c8edf33f3302969ba480a327", local_dir=base)
checkpoint = uzbek / "checkpoints" / "large_full_600m" / "best.pt"
expected = "79847b8d139acb9cbc662329a0a52fe82676013a8c2b19ff2dad38b2906511a3"
def valid_checkpoint():
    if not checkpoint.is_file():
        return False
    digest = hashlib.sha256()
    with checkpoint.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest() == expected
if not valid_checkpoint():
    hf_hub_download("rustam1221/uzbek-asr-gigaam",
                    "checkpoints/large_full_600m/best.pt", local_dir=uzbek,
                    revision="304f81948f40ae51a8f718926abd242f095edd84",
                    force_download=checkpoint.is_file())
if not all((base / name).is_file() for name in ("config.json", "modeling_gigaam.py")):
    raise RuntimeError("GigaAM asosiy fayllari yuklanmadi")
if not valid_checkpoint():
    raise RuntimeError("GigaAM Uzbek 600M modeli yuklanmadi")
"""

VERIFY_RUNTIME = r"""
import faulthandler
import os
os.environ["ORT_DISABLE_TELEMETRY"]="1"
import gc
import sys
import tempfile
import wave
from pathlib import Path
faulthandler.enable()

runtime = Path(sys.argv[1])
os.environ["HF_MODULES_CACHE"]=str(runtime/"models"/".hf-modules")
sys.path.insert(0, str(runtime))
from PIL import Image, ImageFont
from subtitles.animations import font_path
ImageFont.truetype(font_path(), 24)
import torch
from faster_whisper import WhisperModel
model = WhisperModel(str(runtime / "models" / "large-v3"),
                     device="cpu", compute_type="int8", local_files_only=True)
del model
gc.collect()
from subtitles.gigaam import transcribe
with tempfile.TemporaryDirectory(prefix="uzscribe-check-") as temporary:
    audio = Path(temporary) / "silence.wav"
    with wave.open(str(audio), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b"\0\0" * 16000)
    from subtitles.cli import transcribe as caption_transcribe
    caption_transcribe(audio, "large-v3", "auto")
    caption_transcribe(audio, "navai-medium", "auto")
    from subtitles.speakers import diarize
    diarize(audio,runtime/"models/speaker-onnx")
    from subtitles.sentences import local_corrector
    correct=local_corrector(runtime)
    if correct is None:raise RuntimeError("Matn modeli yuklanmagan")
    correct("Salom.")
    del correct
    gc.collect()
    transcribe(audio, runtime / "models" / "gigaam-base-large",
               runtime / "models" / "gigaam-uzbek" / "checkpoints" /
               "large_full_600m" / "best.pt", "cpu")
print("UzScribe: Whisper, GigaAM, NavAI, matn, so‘zlovchilar va audio tekshiruvi o‘tdi.", flush=True)
"""


def _retry_download(command: list[str]) -> None:
    for attempt in range(3):
        try:
            subprocess.run(command, check=True)
            return
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise
            print("Yuklash uzildi. Qayta urinilmoqda…", flush=True)
            time.sleep(2 * (attempt + 1))


def _python_for(runtime: Path, system: str) -> Path:
    return runtime / ".venv" / ("Scripts/python.exe" if system == "win32" else "bin/python")


def _intel_mac(system: str) -> bool:
    return system == "darwin" and platform.machine().lower() in {"x86_64", "amd64"}


def _navai_ready(directory: Path) -> bool:
    return (all((directory / name).is_file()
                for name in ("model.bin", "config.json", "tokenizer.json"))
            and (directory / "model.bin").stat().st_size >= 100_000_000)


def _prepare_environment(runtime: Path, system: str, *, convert: bool,
                         uv: Path | None = None) -> Path:
    python = _python_for(runtime, system)
    if python.is_file():
        try:
            healthy = subprocess.run(
                [str(python), "-c", "import sys; assert (3,10) <= sys.version_info[:2] < (3,13)"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        except OSError:
            healthy = False
        if not healthy:
            backup = runtime / (".venv-backup-" + uuid.uuid4().hex)
            (runtime / ".venv").rename(backup)
            print(f"Python muhiti qayta yaratilmoqda. Eski nusxa: {backup}", flush=True)
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
    requirements = "requirements-intel-mac.txt" if _intel_mac(system) else "requirements-release.txt"
    subprocess.run([*base_command, "-r", str(ROOT / "subtitles" / requirements)], check=True)
    if convert and not _intel_mac(system):
        subprocess.run([*base_command, *CONVERTER_DEPENDENCIES], check=True)
    return python


def _install_gigaam(runtime: Path, python: Path, uv: Path | None) -> None:
    if uv:
        command = [str(uv), "pip", "install", "--python", str(python)]
    else:
        command = [str(python), "-m", "pip", "install", "--disable-pip-version-check"]
    requirements = "requirements-intel-mac.txt" if _intel_mac(sys.platform) else "requirements-gigaam.txt"
    subprocess.run([*command, "-r", str(ROOT / "subtitles" / requirements),
                    "huggingface_hub>=0.34,<2"], check=True)
    subprocess.run([str(python), "-c", "import torch, torchaudio, hydra, soundfile, transformers, huggingface_hub"],
                   check=True)
    print("GigaAM Uzbek 600M yuklanmoqda (taxminan 2.3 GB)…", flush=True)
    _retry_download([str(python), "-c", DOWNLOAD_GIGAAM, str(runtime)])


def _install_features(runtime: Path, python: Path, uv: Path | None) -> None:
    command=([str(uv),'pip','install','--python',str(python)] if uv else
             [str(python),'-m','pip','install','--disable-pip-version-check'])
    subprocess.run([*command,'-r',str(ROOT/'subtitles/requirements-speakers.txt')],check=True)
    _retry_download([str(python),str(runtime/'subtitles/model_assets.py'),str(runtime)])


def _verify_installation(runtime: Path, panel: Path, python: Path) -> None:
    if not python.is_file():
        raise RuntimeError("UzScribe Python muhiti topilmadi")
    if not _navai_ready(runtime / "models" / "large-v3"):
        raise RuntimeError("UzScribe Global modeli to‘liq o‘rnatilmadi")
    base = runtime / "models" / "gigaam-base-large"
    if not all((base / name).is_file() for name in ("config.json", "modeling_gigaam.py")):
        raise RuntimeError("GigaAM asosiy fayllari to‘liq o‘rnatilmadi")
    checkpoint = (runtime / "models" / "gigaam-uzbek" / "checkpoints" /
                  "large_full_600m" / "best.pt")
    if not checkpoint.is_file() or checkpoint.stat().st_size < 100_000_000:
        raise RuntimeError("GigaAM Uzbek 600M checkpointi to‘liq o‘rnatilmadi")
    require_features(runtime)
    for name in ("CSXS/manifest.xml", "index.html", "panel.js", "license-core.js", "license-panel.js", "license-config.json", "animation-panel.js", "podcast-panel.js", "reels-panel.js", "text-tools-panel.js", "panel-ui.js",
                 "assets/uzscribe-logo.jpg", "host/editor.jsx", "host/after_effects.jsx"):
        if not (panel / name).is_file():
            raise RuntimeError(f"Adobe panel fayli yetishmayapti: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub’dan UzScribe o‘rnatish")
    parser.add_argument("--model-dir", type=Path,
                        help="Mavjud CTranslate2 UzScribe Global modeli; yuklashni o‘tkazib yuboradi")
    args = parser.parse_args()
    if not (3, 10) <= sys.version_info[:2] < (3, 13):
        parser.error("Python 3.10, 3.11 yoki 3.12 kerak")
    try:
        runtime, panel = destinations(sys.platform, Path.home(), dict(os.environ))
        existing = runtime / "models" / "large-v3"
        if args.model_dir and not _navai_ready(args.model_dir):
            raise FileNotFoundError(f"UzScribe Global modeli to‘liq emas: {args.model_dir}")
        model = args.model_dir or (existing if _navai_ready(existing) else None)
        uv = Path(os.environ["UZSCRIBE_UV_BIN"]) if os.environ.get("UZSCRIBE_UV_BIN") else None
        python = _prepare_environment(runtime, sys.platform, convert=model is None, uv=uv)
        if model is None:
            with tempfile.TemporaryDirectory(prefix="uzscribe-model-") as temporary:
                print("UzScribe Global yuklanmoqda (taxminan 3.1 GB)…", flush=True)
                _retry_download([str(python), "-c", CONVERT, MODEL_REPO,
                                 MODEL_REVISION, temporary])
                install(ROOT, sys.platform, Path.home(), dict(os.environ),
                        developer=False, skip_dependencies=True,
                        model_source=Path(temporary) / "converted")
        else:
            install(ROOT, sys.platform, Path.home(), dict(os.environ),
                    developer=False, skip_dependencies=True, model_source=model)
        subprocess.run([str(python), "-c", "import faster_whisper, imageio_ffmpeg"], check=True)
        _install_gigaam(runtime, python, uv)
        _install_features(runtime, python, uv)
        print("Modellar amalda ishga tushirib tekshirilmoqda…", flush=True)
        subprocess.run([str(python), "-c", VERIFY_RUNTIME, str(runtime)], check=True)
        _copy_panel(ROOT, panel)
        _enable_debug(sys.platform)
        _verify_installation(runtime, panel, python)
        (runtime/'install-report.json').write_text(json.dumps({'version':'0.7.0',
            'ready':True,'models':['large-v3','gigaam-uzbek','navai-medium','rubai-transcript','speaker-onnx'],
            'verified':['audio','silero-vad','animations','caption-asr','text-correction','speaker-diarization']},ensure_ascii=False,indent=2),encoding='utf-8')
        print('Tayyor: Scribe Giga, Scribe Nav, Whisper, matn tartiblash, so‘zlovchilar, audio va animatsiyalar.',flush=True)
        # Only plugin-owned weak models are removed after successful verification.
        import shutil
        for name in ("navai-small", "small", "tiny"):
            old = runtime / "models" / name
            if old.is_dir() and not old.is_symlink():
                shutil.rmtree(old)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"UzScribe o‘rnatilmadi: {exc}", file=sys.stderr)
        return 1
    print("UzScribe o‘rnatildi. Premiere Pro yoki After Effects’ni qayta oching.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
