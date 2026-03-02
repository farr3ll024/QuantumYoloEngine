from __future__ import annotations

from pathlib import Path


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def normalize_path(value: str) -> str:
    p = Path(value).expanduser()
    ensure_parent_dir(p)
    return str(p)