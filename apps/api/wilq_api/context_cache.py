from __future__ import annotations

import os
from dataclasses import dataclass
from time import monotonic
from typing import Any

from apps.api.wilq_api.context_models import ContextPackRequest

DEFAULT_SKILL_CONTEXT_CACHE_SECONDS = 5.0
_cached_skill_context_packs: dict[str, SkillContextCacheEntry] = {}


@dataclass(frozen=True)
class SkillContextCacheEntry:
    created_at: float
    payload: dict[str, Any]


def request_skill(request: ContextPackRequest | None) -> str | None:
    if request is None:
        return None
    return request.skill or request.skill_id


def clear_skill_context_cache() -> None:
    _cached_skill_context_packs.clear()


def read_skill_context_cache(request: ContextPackRequest) -> dict[str, Any] | None:
    cache_seconds = _skill_context_cache_seconds()
    if cache_seconds <= 0:
        return None
    cached = _cached_skill_context_packs.get(_skill_context_cache_key(request))
    if cached is None:
        return None
    if monotonic() - cached.created_at > cache_seconds:
        return None
    return cached.payload


def write_skill_context_cache(request: ContextPackRequest, payload: dict[str, Any]) -> None:
    if _skill_context_cache_seconds() <= 0:
        return
    _cached_skill_context_packs[_skill_context_cache_key(request)] = SkillContextCacheEntry(
        created_at=monotonic(),
        payload=payload,
    )


def _skill_context_cache_key(request: ContextPackRequest) -> str:
    return "|".join(
        [
            request_skill(request) or "",
            request.focus or "",
            str(request.max_opportunities),
        ]
    )


def _skill_context_cache_seconds() -> float:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0.0
    configured = os.getenv("WILQ_SKILL_CONTEXT_CACHE_SECONDS")
    if configured is None:
        return DEFAULT_SKILL_CONTEXT_CACHE_SECONDS
    try:
        return max(0.0, float(configured))
    except ValueError:
        return DEFAULT_SKILL_CONTEXT_CACHE_SECONDS
