from __future__ import annotations

import os
import shlex
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ACCESS_PACK = Path.home() / "ekologus-access-pack-20260617-120758"

VARIABLE_ALIASES: dict[str, tuple[str, ...]] = {
    "AHREFS_API_TOKEN": ("AHREFS_API_KEY",),
    "GOOGLE_SHEETS_REVIEW_SPREADSHEET_ID": ("GOOGLE_SHEETS_SPREADSHEET_ID",),
    "WORDPRESS_EKOLOGUS_URL": ("EKOLOGUS_WP_STAGING_URL", "MIS_PRIMARY_SITE_URL"),
    "WORDPRESS_EKOLOGUS_USERNAME": ("EKOLOGUS_WP_STAGING_USER",),
    "WORDPRESS_EKOLOGUS_APP_PASSWORD": ("EKOLOGUS_WP_STAGING_APP_PASSWORD",),
    "WORDPRESS_SKLEP_URL": ("MIS_SHOP_SITE_URL",),
}


def local_env_path() -> Path:
    configured_path = os.getenv("WILQ_ENV_FILE")
    if configured_path:
        return Path(configured_path)
    return PROJECT_ROOT / ".env"


def load_local_env() -> None:
    load_dotenv(local_env_path(), override=False)


def access_pack_path() -> Path:
    return Path(os.getenv("WILQ_ACCESS_PACK_PATH", str(DEFAULT_ACCESS_PACK)))


def local_env_key_names(path: Path | None = None) -> set[str]:
    return set(local_env_values(path).keys())


def local_env_values(path: Path | None = None) -> dict[str, str]:
    env_file = path or local_env_path()
    return env_file_values(env_file)


def access_pack_env_key_names(path: Path | None = None) -> set[str]:
    return set(access_pack_env_values(path).keys())


def access_pack_env_values(path: Path | None = None) -> dict[str, str]:
    pack = path or access_pack_path()
    return env_file_values(pack / "ekologus.env")


def env_file_values(env_file: Path) -> dict[str, str]:
    if not env_file.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = _clean_env_value(value)
    return values


def _clean_env_value(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    try:
        parsed = shlex.split(stripped, comments=False, posix=True)
    except ValueError:
        return stripped.strip("'\"")
    if not parsed:
        return ""
    return parsed[0]


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
    return variable_value(name, path=path) is not None or _credential_file_fallback_available(
        name,
        path,
    )


def variable_value(name: str, path: Path | None = None) -> str | None:
    for candidate in _candidate_names(name):
        env_value = os.getenv(candidate)
        if env_value:
            return env_value
    access_pack_values = access_pack_env_values(path)
    for candidate in _candidate_names(name):
        access_pack_value = access_pack_values.get(candidate)
        if access_pack_value:
            return access_pack_value
    return None


def variable_source(name: str, path: Path | None = None) -> str | None:
    local_values = local_env_values()
    for candidate in _candidate_names(name):
        env_value = os.getenv(candidate)
        if env_value:
            return "repo_env" if local_values.get(candidate) == env_value else "process_env"
    access_pack_values = access_pack_env_values(path)
    for candidate in _candidate_names(name):
        if access_pack_values.get(candidate):
            return "access_pack_env"
    if _credential_file_fallback_available(name, path):
        return "access_pack_credentials"
    return None


def credential_source_summary(names: Iterable[str], path: Path | None = None) -> list[str]:
    sources: list[str] = []
    for name in names:
        source = variable_source(name, path=path)
        if source and source not in sources:
            sources.append(source)
    return sources


def credential_runtime_status(
    path: Path | None = None,
    *,
    detailed: bool = False,
) -> dict[str, Any]:
    pack = path or access_pack_path()
    env_file = local_env_path()
    status: dict[str, Any] = {
        "primary_source": "repo_env" if env_file.exists() else "access_pack_env",
        "source_order": [
            "process_env",
            "repo_env",
            "access_pack_env",
            "access_pack_credentials",
        ],
        "repo_env_file_present": env_file.exists(),
        "repo_env_key_count": len(local_env_key_names(env_file)),
        "access_pack_present": pack.exists(),
        "access_pack_env_file_present": (pack / "ekologus.env").exists(),
        "access_pack_env_key_count": len(access_pack_env_key_names(pack)),
        "credential_file_count": len(credential_file_names(pack)),
        "manifest_file_count": len(manifest_file_names(pack)),
        "secrets_redacted": True,
    }
    if detailed:
        status.update(
            {
                "repo_env_path": str(env_file),
                "access_pack_path": str(pack),
                "credential_files_present": credential_file_names(pack),
                "manifest_files": manifest_file_names(pack),
            }
        )
    return status


def access_pack_status(path: Path | None = None, *, detailed: bool = False) -> dict[str, Any]:
    runtime = credential_runtime_status(path, detailed=detailed)
    status: dict[str, Any] = {
        "exists": runtime["access_pack_present"],
        "env_file_present": runtime["access_pack_env_file_present"],
        "env_key_count": runtime["access_pack_env_key_count"],
        "credential_file_count": runtime["credential_file_count"],
        "manifest_file_count": runtime["manifest_file_count"],
        "secrets_redacted": True,
    }
    if detailed:
        status.update(
            {
                "path": runtime["access_pack_path"],
                "credential_files_present": runtime["credential_files_present"],
                "manifest_files": runtime["manifest_files"],
            }
        )
    return status


def _candidate_names(name: str) -> tuple[str, ...]:
    return (name, *VARIABLE_ALIASES.get(name, ()))


def _credential_file_fallback_available(name: str, path: Path | None = None) -> bool:
    return name == "GOOGLE_APPLICATION_CREDENTIALS" and bool(credential_file_names(path))
