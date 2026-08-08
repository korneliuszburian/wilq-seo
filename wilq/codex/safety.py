from __future__ import annotations

from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field

from wilq.security.redaction import redact_mapping


class CodexPromptSafety(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed: bool
    reason: str
    prompt_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    redacted_fields: list[str] = Field(default_factory=list)


def assess_codex_prompt(prompt: str, *, dry_run: bool) -> CodexPromptSafety:
    digest = sha256(prompt.encode("utf-8")).hexdigest()
    redacted_prompt = redact_mapping({"prompt": prompt})["prompt"]
    redacted_fields = [] if redacted_prompt == prompt else ["prompt"]
    if redacted_fields:
        return CodexPromptSafety(
            allowed=False,
            reason="prompt_contains_redacted_secret",
            prompt_digest=digest,
            redacted_fields=redacted_fields,
        )
    if dry_run:
        return CodexPromptSafety(
            allowed=False,
            reason="dry_run_digest_only",
            prompt_digest=digest,
            redacted_fields=[],
        )
    return CodexPromptSafety(
        allowed=True,
        reason="prompt_safe",
        prompt_digest=digest,
        redacted_fields=[],
    )


__all__ = ["CodexPromptSafety", "assess_codex_prompt"]
