"""Build a clean buyer ZIP with the commercially licensed UzScribe Global model."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PANEL = ("CSXS/manifest.xml", "index.html", "panel.js", "license-core.js", "license-panel.js", "license-config.json", "animation-panel.js", "podcast-panel.js", "reels-panel.js", "text-tools-panel.js", "assets/uzscribe-logo.jpg",
         "host/editor.jsx", "host/after_effects.jsx")
RUNTIME = ("__init__.py", "podcast.py", "reels.py", "cli.py", "batch.py", "animations.py", "sentences.py", "gigaam.py",
           "fastconformer.py", "requirements.txt", "requirements-release.txt",
           "requirements-gigaam.txt", "requirements-fastconformer.txt",
           "requirements-intel-mac.txt",
           "requirements-speakers.txt")
MODEL = ("model.bin", "config.json", "preprocessor_config.json", "tokenizer.json",
         "vocabulary.json")


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(model_dir: Path, output: Path, signed_zxp: Path | None = None, license_config: Path | None = None) -> None:
    files: dict[str, Path] = {
        "install.py": ROOT / "install.py",
        "install_online.py": ROOT / "install_online.py",
        "README-INSTALL.md": ROOT / "README-INSTALL.md",
        "NOTICE-THIRD-PARTY.md": ROOT / "NOTICE-THIRD-PARTY.md",
        "APACHE-2.0.txt": ROOT / "APACHE-2.0.txt",
        "WHISPER-LICENSE.txt": ROOT / "WHISPER-LICENSE.txt",
        "docs/PODCAST-RESEARCH.md": ROOT / "docs/PODCAST-RESEARCH.md",
        "docs/REELS-RESEARCH.md": ROOT / "docs/REELS-RESEARCH.md",
        "docs/ANIMATIONS.md": ROOT / "docs/ANIMATIONS.md",
        "Install-mac.command": ROOT / "Install-mac.command",
        "Install-Windows.ps1": ROOT / "Install-Windows.ps1",
        "bootstrap-mac.sh": ROOT / "bootstrap-mac.sh",
        "bootstrap-windows.ps1": ROOT / "bootstrap-windows.ps1",
    }
    files.update({f"adobe/UzbekSubtitles/{name}": ROOT / "adobe" / "UzbekSubtitles" / name
                  for name in PANEL})
    if license_config:
        config = json.loads(license_config.read_text())
        if config.get("mode") != "subscription" or not str(config.get("api_url", "")).startswith("https://") or "BEGIN PUBLIC KEY" not in str(config.get("public_key", "")) or "PRIVATE KEY" in str(config):
            raise ValueError("Paid license configuration must contain an HTTPS API and a public RSA key only")
        if signed_zxp:
            raise ValueError("Configure the panel before signing ZXP; do not override its signed license configuration")
        files["adobe/UzbekSubtitles/license-config.json"] = license_config
    files.update({f"subtitles/{name}": ROOT / "subtitles" / name for name in RUNTIME})
    files.update({f"models/large-v3/{name}": model_dir / name for name in MODEL})
    if signed_zxp:
        files["UzScribe.zxp"] = signed_zxp
    missing = [name for name, path in files.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Release fayllari topilmadi: " + ", ".join(missing))
    checksums = {name: hash_file(path)
                 for name, path in files.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip", delete=False) as tmp:
        temporary = Path(tmp.name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, path in files.items():
                archive.write(path, name)
            archive.writestr("checksums.json", json.dumps(checksums, indent=2) + "\n")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--signed-zxp", type=Path)
    parser.add_argument("--license-config", type=Path, help="Public subscription config for a paid buyer ZIP")
    args = parser.parse_args()
    build(args.model_dir, args.output, args.signed_zxp, args.license_config)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
