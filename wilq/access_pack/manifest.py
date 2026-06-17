from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DEFAULT_ACCESS_PACK = Path("/home/krn/ekologus-access-pack-20260617-120758")


def access_pack_path() -> Path:
    return Path(os.getenv("WILQ_ACCESS_PACK_PATH", str(DEFAULT_ACCESS_PACK)))


def env_key_names(path: Path | None = None) -> set[str]:
    pack = path or access_pack_path()
    env_file = pack / "ekologus.env"
    if not env_file.exists():
        return set()
    keys: set[str] = set()
    for raw_line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        key = line.split("=", 1)[0].strip()
        if key:
            keys.add(key)
    return keys


def credential_file_names(path: Path | None = None) -> list[str]:
    pack = path or access_pack_path()
    credential_dir = pack / "credentials"
    if not credential_dir.exists():
        return []
    return sorted(item.name for item in credential_dir.iterdir() if item.is_file())


def manifest_file_names(path: Path | None = None) -> list[str]:
    pack = path or access_pack_path()
    if not pack.exists():
        return []
    return sorted(str(item.relative_to(pack)) for item in pack.rglob("*") if item.is_file())


def variable_available(name: str, path: Path | None = None) -> bool:
    return bool(os.getenv(name)) or name in env_key_names(path)


def access_pack_status(path: Path | None = None, *, detailed: bool = False) -> dict[str, Any]:
    pack = path or access_pack_path()
    status: dict[str, Any] = {
        "exists": pack.exists(),
        "env_file_present": (pack / "ekologus.env").exists(),
        "env_key_count": len(env_key_names(pack)),
        "credential_file_count": len(credential_file_names(pack)),
        "manifest_file_count": len(manifest_file_names(pack)),
        "secrets_redacted": True,
    }
    if detailed:
        status.update(
            {
                "path": str(pack),
                "credential_files_present": credential_file_names(pack),
                "manifest_files": manifest_file_names(pack),
            }
        )
    return status
