from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

MODEL_POLICY_NOTES = [
    "WILQ API pozostaje niezależne od modelu.",
    "Skille Codexa używają kontraktów API i nie mogą dopowiadać metryk marketingowych.",
    "Krytyczne workflowy muszą używać oczekiwanych schematów odpowiedzi.",
    "Zmiana modelu albo runtime nie może ominąć dowodów źródłowych, sprawdzenia akcji ani audytu.",
]

_SAFE_MODEL_VALUE_LENGTH = 200


def configured_codex_model() -> str | None:
    return _configured_scalar("model")


def configured_codex_reasoning_effort() -> str | None:
    return _configured_scalar("model_reasoning_effort")


def _configured_scalar(key: str) -> str | None:
    config = _codex_config()
    value = config.get(key)
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if 0 < len(value) <= _SAFE_MODEL_VALUE_LENGTH else None


def _codex_config() -> dict[str, Any]:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        config_path = Path(codex_home).expanduser() / "config.toml"
    else:
        home = os.environ.get("HOME")
        if not home:
            return {}
        config_path = Path(home).expanduser() / ".codex" / "config.toml"
    try:
        value = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}
    return value


__all__ = [
    "MODEL_POLICY_NOTES",
    "configured_codex_model",
    "configured_codex_reasoning_effort",
]
