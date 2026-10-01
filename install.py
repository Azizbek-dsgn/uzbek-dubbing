"""Install the local subtitle runtime and a CEP beta panel for one user."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path


def destinations(system: str, home: Path, environment: dict[str, str]) -> tuple[Path, Path]:
    if system == "win32":
        local = Path(environment.get("LOCALAPPDATA") or home / "AppData" / "Local")
        roaming = Path(environment.get("APPDATA") or home / "AppData" / "Roaming")
        return local / "UzbekSubtitles", roaming / "Adobe" / "CEP" / "extensions" / "UzbekSubtitles"
    if system == "darwin":
        return (home / "Library" / "Application Support" / "UzbekSubtitles",
                home / "Library" / "Application Support" / "Adobe" / "CEP" / "extensions" / "UzbekSubtitles")
    raise RuntimeError("Faqat macOS va Windows qo‘llanadi")


def _copy_runtime(package: Path, target: Path, model_source: Path | None = None) -> None:
    target.mkdir(parents=True, exist_ok=True)
    source = package / "subtitles"
    if not (source / "cli.py").is_file():
        raise FileNotFoundError("subtitles/cli.py paketda yo‘q")
    dest = target / "subtitles"
    dest.mkdir(exist_ok=True)
    for path in source.iterdir():
        if path.is_file() and path.suffix in {".py", ".txt"}:
            shutil.copy2(path, dest / path.name)
    model = model_source or package / "models" / "large-v3"
    if not (model / "model.bin").is_file():
        raise FileNotFoundError("UzScribe Global modeli paketda yo‘q")
    model_target = target / "models" / "large-v3"
    model_target.mkdir(parents=True, exist_ok=True)
    for path in model.iterdir():
        if path.is_file() and path.resolve() != (model_target / path.name).resolve():
            shutil.copy2(path, model_target / path.name)


def _verify_package(package: Path) -> None:
    manifest = package / "checksums.json"
    if not manifest.is_file():
        return
    for name, expected in json.loads(manifest.read_text(encoding="utf-8")).items():
        path = package / name
        digest = hashlib.sha256()
        if not path.is_file():
            raise RuntimeError(f"Paket fayli buzilgan: {name}")
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise RuntimeError(f"Paket fayli buzilgan: {name}")


def _copy_panel(package: Path, target: Path) -> None:
    source = package / "adobe" / "UzbekSubtitles"
    if not (source / "CSXS" / "manifest.xml").is_file():
        raise FileNotFoundError("Adobe panel paketda yo‘q")
    if target.is_symlink():
        existing_manifest = target / "CSXS" / "manifest.xml"
        if not existing_manifest.is_file() or "uz.azizbek.subtitles.panel" not in existing_manifest.read_text(encoding="utf-8"):
            raise RuntimeError(f"Boshqa panel symlink: {target}. Uni qo‘lda tekshiring.")
    target.mkdir(parents=True, exist_ok=True)
    for folder in ("CSXS", "host"):
        shutil.copytree(source / folder, target / folder, dirs_exist_ok=True)
    if (source / "assets").is_dir():
        shutil.copytree(source / "assets", target / "assets", dirs_exist_ok=True)
    for name in ("index.html", "panel.js", "podcast-panel.js"):
        shutil.copy2(source / name, target / name)


def _enable_debug(system: str) -> None:
    if system == "darwin":
        for version in ("9", "10", "11", "12", "13"):
            subprocess.run(["defaults", "write", f"com.adobe.CSXS.{version}",
                            "PlayerDebugMode", "1"], check=True)
    else:
        import winreg
        for version in ("9", "10", "11", "12", "13"):
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                  rf"Software\Adobe\CSXS.{version}") as key:
                winreg.SetValueEx(key, "PlayerDebugMode", 0, winreg.REG_SZ, "1")


def install(package: Path, system: str, home: Path, environment: dict[str, str],
            *, developer: bool, skip_dependencies: bool = False,
            model_source: Path | None = None) -> tuple[Path, Path]:
    runtime, panel = destinations(system, home, environment)
    _verify_package(package)
    _copy_runtime(package, runtime, model_source)
    venv_python = runtime / ".venv" / ("Scripts/python.exe" if system == "win32" else "bin/python")
    if not skip_dependencies:
        if not venv_python.is_file():
            venv.EnvBuilder(with_pip=True).create(runtime / ".venv")
        subprocess.run([str(venv_python), "-m", "pip", "install", "--disable-pip-version-check",
                        "-r", str(runtime / "subtitles" / "requirements-release.txt")], check=True)
        subprocess.run([str(venv_python), "-c", "import faster_whisper, imageio_ffmpeg"], check=True)
    if developer:
        _copy_panel(package, panel)
        _enable_debug(system)
    return runtime, panel


def main() -> int:
    parser = argparse.ArgumentParser(description="UzScribe o‘rnatish")
    parser.add_argument("--developer", action="store_true",
                        help="Beta: imzosiz CEP panelni ko‘chirib, Adobe debug rejimini yoqish")
    args = parser.parse_args()
    if not (3, 10) <= sys.version_info[:2] < (3, 13):
        parser.error("Python 3.10, 3.11 yoki 3.12 kerak")
    try:
        runtime, panel = install(Path(__file__).resolve().parent, sys.platform,
                                 Path.home(), dict(os.environ), developer=args.developer)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"O‘rnatish tugamadi: {exc}", file=sys.stderr)
        return 1
    print(f"Model va Python o‘rnatildi: {runtime}")
    if args.developer:
        print(f"Beta panel o‘rnatildi: {panel}")
    else:
        print("Panel uchun imzolangan ZXP faylini Adobe orqali o‘rnating.")
    print("Premiere Pro va After Effects’ni qayta oching.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
