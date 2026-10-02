#!/bin/zsh
set -e
script_dir="$(cd "$(dirname "$0")" && pwd)"
UZSCRIBE_SOURCE_DIR="$script_dir" bash "$script_dir/bootstrap-mac.sh"
