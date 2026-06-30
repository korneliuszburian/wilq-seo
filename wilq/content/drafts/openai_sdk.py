from __future__ import annotations

import os
from collections.abc import Mapping
from typing import cast

from wilq.content.drafts.openai_runtime import OpenAIClientProtocol

OPENAI_STRUCTURED_DRAFT_LIVE_ENV = "WILQ_OPENAI_STRUCTURED_DRAFT_LIVE_ENABLED"


def openai_structured_draft_live_enabled(
    environ: Mapping[str, str] | None = None,
) -> bool:
    env = os.environ if environ is None else environ
    return env.get(OPENAI_STRUCTURED_DRAFT_LIVE_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def build_openai_sdk_client(
    environ: Mapping[str, str] | None = None,
) -> OpenAIClientProtocol | None:
    env = os.environ if environ is None else environ
    api_key = env.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    return cast(OpenAIClientProtocol, OpenAI(api_key=api_key))
