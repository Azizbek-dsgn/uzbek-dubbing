"""Space checks for the installer; never delete shared caches or user media."""
from __future__ import annotations

import errno
import os
from pathlib import Path
import shutil
import sys

GIB = 1024 ** 3
SPACE_EXIT = 28
RESERVE = GIB


class InsufficientSpace(RuntimeError):
    pass


def is_disk_full(error):
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, InsufficientSpace) or (
            isinstance(error, OSError) and
            (error.errno == errno.ENOSPC or getattr(error, 'winerror', None) in (39, 112))
        ):
            return True
        error = error.__cause__ or error.__context__
    return False


def require_space(path: Path, needed: int, phase: str):
    existing = path.resolve()
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    free = shutil.disk_usage(existing).free
    if free < needed:
        raise InsufficientSpace(
            f'{phase}: diskda joy yetarli emas. {path}: '
            f'bo‘sh {free/GIB:.1f} GiB, kerak kamida {needed/GIB:.1f} GiB. '
            'Shu diskda joy bo‘shatib, o‘rnatish buyrug‘ini qayta bajaring. '
            'Yuklangan model fayllari saqlanadi.')


def large_file(path):
    return path.is_file() and path.stat().st_size >= 100_000_000


def navai_download_dir(runtime):
    # Immutable upstream revision; a different model version gets its own cache.
    return runtime/'models'/'.downloads'/'navai-9c67dea55c8ac11f237d60ca0c32e5dc5a8c3de5'


def navai_download_budget(runtime):
    source = navai_download_dir(runtime)
    # Only finalized weights count. HF *.incomplete downloads are not complete.
    cached = sum(p.stat().st_size for p in source.glob('*.safetensors') if p.is_file())
    return max(0, int(3.5*GIB)-cached) + int(1.2*GIB)


def installation_budget(runtime, *, global_ready=False):
    models = runtime/'models'
    needed = RESERVE + (2*GIB if (runtime/'.venv').is_dir() else 7*GIB)
    if not global_ready:
        needed += 4*GIB
    if not large_file(models/'gigaam-uzbek/checkpoints/large_full_600m/best.pt'):
        needed += 3*GIB
    if not all((models/'navai-medium'/name).is_file() for name in
               ('config.json', 'tokenizer.json', 'preprocessor_config.json')) or not large_file(models/'navai-medium/model.bin'):
        needed += navai_download_budget(runtime)
    if not large_file(models/'rubai-transcript/model.safetensors'):
        needed += int(1.6*GIB)
    needed += int(.1*GIB)  # speaker assets, panel, metadata
    return needed


def disk_full_message():
    return ('Diskda joy tugadi. Model yoki Python fayllari yozilmadi. '
            'O‘rnatish diskida joy bo‘shatib, shu buyruqni qayta bajaring. '
            'Yuklangan modellarni o‘chirish kerak emas.')


def install_error_hook():
    """Return a nonretryable code even when a download library wraps ENOSPC."""
    original = sys.excepthook
    def hook(kind, error, traceback):
        if is_disk_full(error):
            print(str(error) if isinstance(error, InsufficientSpace) else disk_full_message(),
                  file=sys.stderr, flush=True)
            os._exit(SPACE_EXIT)
        original(kind, error, traceback)
    sys.excepthook = hook
