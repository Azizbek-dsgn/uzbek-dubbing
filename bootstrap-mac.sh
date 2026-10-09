#!/bin/bash
set -euo pipefail
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

SOURCE_URL="https://codeload.github.com/Azizbek-dsgn/UzScribe/tar.gz/refs/heads/main"
log_root="$HOME/Library/Application Support/UzbekSubtitles"
mkdir -p "$log_root"
log_path="$log_root/install.log"
exec > >(tee -a "$log_path") 2>&1
work=$(mktemp -d "${TMPDIR:-/tmp}/uzscribe.XXXXXX")
finish() {
  result=$?
  if [[ "$result" -eq 0 ]]; then
    echo "UzScribe o‘rnatildi. Jurnal: $log_path"
  else
    echo "UzScribe o‘rnatish tugamadi (kod $result). Jurnal: $log_path" >&2
  fi
  rm -rf "$work"
  exit "$result"
}
trap finish EXIT

# Check bootstrap space before downloading Python; the full budget follows.
for check_path in "$log_root" "$work"; do
  available_kib=$(df -Pk "$check_path" | awk 'NR==2 {print $4}')
  if [[ "$available_kib" =~ ^[0-9]+$ ]] && (( available_kib < 1048576 )); then
    echo "$check_path: diskda joy yetarli emas. Avval kamida 1 GiB joy bo‘shating; keyingi tekshiruv barcha modellar uchun kerakli joyni ko‘rsatadi." >&2
    exit 28
  fi
done

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
if [[ -f "$source_dir/models/large-v3/model.bin" ]]; then
  install_args+=(--model-dir "$source_dir/models/large-v3")
fi
"$python" "${install_args[@]}"
