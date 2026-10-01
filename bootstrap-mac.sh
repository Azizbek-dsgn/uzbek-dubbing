#!/bin/bash
set -euo pipefail

SOURCE_URL="https://codeload.github.com/Azizbek-dsgn/uzbek-dubbing/tar.gz/refs/heads/feat/uzbek-subtitles-adobe"
work=$(mktemp -d "${TMPDIR:-/tmp}/uzscribe.XXXXXX")
trap 'rm -rf "$work"' EXIT

if [[ -n "${UZSCRIBE_ARCHIVE_PATH:-}" ]]; then
  cp "$UZSCRIBE_ARCHIVE_PATH" "$work/source.tar.gz"
else
  curl --fail --location --silent --show-error --retry 3 "$SOURCE_URL" -o "$work/source.tar.gz"
fi
mkdir "$work/source"
tar -xzf "$work/source.tar.gz" -C "$work/source" --strip-components=1
[[ -f "$work/source/install_online.py" ]] || { echo 'UzScribe kodi topilmadi.' >&2; exit 1; }

python=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; assert (3, 10) <= sys.version_info[:2] < (3, 13)' 2>/dev/null; then
    python=$(command -v "$candidate")
    break
  fi
done
if [[ -z "$python" ]]; then
  echo 'Python 3.12 tayyorlanmoqda…'
  curl --fail --location --silent --show-error --retry 3 https://astral.sh/uv/install.sh -o "$work/uv-install.sh"
  UV_UNMANAGED_INSTALL="$work/uv-bin" sh "$work/uv-install.sh"
  "$work/uv-bin/uv" python install 3.12
  python=$("$work/uv-bin/uv" python find 3.12)
fi

"$python" "$work/source/install_online.py"
