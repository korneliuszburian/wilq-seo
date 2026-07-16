from __future__ import annotations

from pathlib import Path


def prepare_private_store_path(
    path: Path,
    *,
    normalize_existing_parent: bool,
) -> None:
    parent_existed = path.parent.exists()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if normalize_existing_parent or not parent_existed:
        path.parent.chmod(0o700)
    if path.exists():
        path.chmod(0o600)
