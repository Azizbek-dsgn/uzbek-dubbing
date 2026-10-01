#!/bin/zsh
set -e
cd "$(dirname "$0")"
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; assert (3,10) <= sys.version_info[:2] < (3,13)' 2>/dev/null; then
      if [[ -f UzScribe.zxp ]]; then
        "$candidate" install.py
        print 'Endi UzScribe.zxp faylini Adobe orqali o‘rnating.'
      else
        "$candidate" install.py --developer
      fi
      exit 0
    fi
  fi
done
print 'Python 3.10–3.12 kerak: https://www.python.org/downloads/' >&2
exit 1
