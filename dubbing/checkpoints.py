"""Checkpoint persistence so interrupted jobs can resume safely."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def _jsonable(value: Any) -> Any:
    """Convert dataclasses and nested values into JSON-compatible values."""

    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def save_checkpoint(path: str | Path, payload: dict[str, Any]) -> None:
    """Atomically write a checkpoint JSON file."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_jsonable(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(target)


def load_checkpoint(path: str | Path) -> dict[str, Any] | None:
    """Load a checkpoint if it exists and contains valid JSON."""

    target = Path(path)
    if not target.exists():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Checkpoint faylini o‘qib bo‘lmadi: {target}") from exc
