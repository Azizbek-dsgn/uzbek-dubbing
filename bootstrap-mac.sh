#!/bin/bash
set -euo pipefail

SOURCE_URL="https://codeload.github.com/Azizbek-dsgn/uzbek-dubbing/tar.gz/refs/heads/feat/uzbek-subtitles-adobe"
work=$(mktemp -d "${TMPDIR:-/tmp}/uzscribe.XXXXXX")
trap 'rm -rf "$work"' EXIT

if [[ -n "${UZSCRIBE_SOURCE_DIR:-}" ]]; then
  source_dir="$UZSCRIBE_SOURCE_DIR"
else
  if [[ -n "${UZSCRIBE_ARCHIVE_PATH:-}" ]]; then
    cp "$UZSCRIBE_ARCHIVE_PATH" "$work/source.tar.gz"
  else
    curl --fail --location --silent --show-error --retry 3 "$SOURCE_URL" -o "$work/source.tar.gz"
  fi
  mkdir "$work/source"
  tar -xzf "$work/source.tar.gz" -C "$work/source" --strip-components=1
  source_dir="$work/source"
fi
[[ -f "$source_dir/install_online.py" ]] || { echo 'UzScribe kodi topilmadi.' >&2; exit 1; }

echo 'Python muhiti tayyorlanmoqda…'
if [[ -n "${UZSCRIBE_UV_BIN:-}" && -x "$UZSCRIBE_UV_BIN" ]]; then
  uv="$UZSCRIBE_UV_BIN"
else
  curl --fail --location --silent --show-error --retry 3 https://astral.sh/uv/install.sh -o "$work/uv-install.sh"
  UV_UNMANAGED_INSTALL="$work/uv-bin" sh "$work/uv-install.sh"
  uv="$work/uv-bin/uv"
fi
[[ -x "$uv" ]] || { echo 'uv o‘rnatilmadi.' >&2; exit 1; }
export UZSCRIBE_UV_BIN="$uv"

python=""
for candidate in python3.12 python3.11 python3.10 python3; do
  [[ "${UZSCRIBE_FORCE_MANAGED_PYTHON:-}" == "1" ]] && break
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; assert (3, 10) <= sys.version_info[:2] < (3, 13)' 2>/dev/null; then
    python=$(command -v "$candidate")
    break
  fi
done
if [[ -z "$python" ]]; then
  echo 'Python 3.12 tayyorlanmoqda…'
  "$uv" python install 3.12
  python=$("$uv" python find 3.12)
  [[ -n "$python" && -x "$python" ]] || { echo 'Python 3.12 fayli topilmadi.' >&2; exit 1; }
fi

install_args=("$source_dir/install_online.py")
if [[ -f "$source_dir/models/navai-small/model.bin" ]]; then
  install_args+=(--model-dir "$source_dir/models/navai-small")
fi
"$python" "${install_args[@]}"
