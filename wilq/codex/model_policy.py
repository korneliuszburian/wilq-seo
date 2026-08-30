from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MODEL_POLICY_NOTES = [
    "WILQ API pozostaje niezależne od modelu.",
    "Skille Codexa używają kontraktów API i nie mogą dopowiadać metryk marketingowych.",
    "Krytyczne workflowy muszą używać oczekiwanych schematów odpowiedzi.",
    "Zmiana modelu albo runtime nie może ominąć dowodów źródłowych, sprawdzenia akcji ani audytu.",
]

_SAFE_MODEL_VALUE_LENGTH = 200
_PROJECT_CODEX_CONFIG_PATH = Path(__file__).resolve().parents[2] / ".codex" / "config.toml"
_CONTENT_RUNTIME_MODEL = "gpt-5.6-terra"
_CONTENT_RUNTIME_REASONING_EFFORT = "max"


@dataclass(frozen=True, slots=True)
class CodexRuntimeSelection:
    """One trusted model selection for every WILQ content app-server turn."""

    model: str
    model_reasoning_effort: str


def configured_codex_runtime_selection() -> CodexRuntimeSelection | None:
    """Return the exact project-pinned selection or fail closed.

    The app-server receives an isolated ``CODEX_HOME`` that contains only the
    operator login. Model selection must therefore come from the tracked WILQ
    configuration rather than the operator's global Codex preferences.
    """

    config = _project_codex_config()
    model = _configured_scalar(config, "model")
    model_reasoning_effort = _configured_scalar(config, "model_reasoning_effort")
    if model != _CONTENT_RUNTIME_MODEL:
        return None
    if model_reasoning_effort != _CONTENT_RUNTIME_REASONING_EFFORT:
        return None
    return CodexRuntimeSelection(
        model=model,
        model_reasoning_effort=model_reasoning_effort,
    )


def configured_codex_model() -> str | None:
    selection = configured_codex_runtime_selection()
    return selection.model if selection is not None else None


def configured_codex_reasoning_effort() -> str | None:
    selection = configured_codex_runtime_selection()
    return selection.model_reasoning_effort if selection is not None else None


def _configured_scalar(config: dict[str, Any], key: str) -> str | None:
    value = config.get(key)
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if 0 < len(value) <= _SAFE_MODEL_VALUE_LENGTH else None


def _project_codex_config() -> dict[str, Any]:
    try:
        value = tomllib.loads(_PROJECT_CODEX_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}
    return value


__all__ = [
    "CodexRuntimeSelection",
    "MODEL_POLICY_NOTES",
    "configured_codex_model",
    "configured_codex_reasoning_effort",
    "configured_codex_runtime_selection",
]
