"""Sign the static CEP panel using Adobe's ZXPSignCmd (seller certificate required)."""

from __future__ import annotations

import argparse
import getpass
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


PANEL = Path(__file__).resolve().parents[1] / "adobe" / "UzbekSubtitles"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True, type=Path, help="Adobe ZXPSignCmd executable")
    parser.add_argument("--certificate", required=True, type=Path, help="Seller .p12 certificate")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timestamp-url", help="RFC 3161 timestamp server URL")
    args = parser.parse_args()
    if not args.tool.is_file() or not args.certificate.is_file():
        parser.error("ZXPSignCmd yoki .p12 sertifikat topilmadi")
    password = os.environ.get("UZ_SUBTITLES_CERT_PASSWORD") or getpass.getpass(".p12 paroli: ")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        staging = Path(temp) / "UzbekSubtitles"
        shutil.copytree(PANEL, staging,
                        ignore=shutil.ignore_patterns(".DS_Store", "__MACOSX", "__pycache__"))
        if any(path.is_symlink() for path in staging.rglob("*")):
            raise RuntimeError("Imzolash papkasida symlink bo‘lmasligi kerak")
        command = [str(args.tool), "-sign", str(staging), str(args.output),
                   str(args.certificate), password]
        if args.timestamp_url:
            command.extend(["-tsa", args.timestamp_url])
        subprocess.run(command, check=True)
    subprocess.run([str(args.tool), "-verify", str(args.output)], check=True)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
