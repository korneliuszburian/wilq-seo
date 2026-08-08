from __future__ import annotations

from hashlib import sha256

import pytest

from wilq.codex.prompts import CODEX_PROMPT_TEMPLATES, resolve_prompt_template
from wilq.codex.safety import assess_codex_prompt


def test_prompt_registry_resolves_versioned_template_and_rejects_unknown_id() -> None:
    template = resolve_prompt_template("content_initial_draft@v1")

    assert template.id == "content_initial_draft"
    assert template.version == 1
    assert template.registry_id == "content_initial_draft@v1"
    assert len(CODEX_PROMPT_TEMPLATES) == 3
    assert "publish_ready=false" in template.render(regulatory_draft_directive="")
    with pytest.raises(KeyError, match="Unknown Codex prompt template"):
        resolve_prompt_template("missing_prompt")


def test_prompt_safety_dry_run_returns_only_a_digest_and_blocks_send() -> None:
    prompt = "Przygotuj bezpieczny szkic do review."

    result = assess_codex_prompt(prompt, dry_run=True)

    assert result.allowed is False
    assert result.reason == "dry_run_digest_only"
    assert result.prompt_digest == sha256(prompt.encode("utf-8")).hexdigest()
    assert result.redacted_fields == []


def test_prompt_safety_blocks_secret_bearing_prompt() -> None:
    prompt = "Użyj sk-" + "x" * 40  # pragma: allowlist secret

    result = assess_codex_prompt(prompt, dry_run=False)

    assert result.allowed is False
    assert result.reason == "prompt_contains_redacted_secret"
    assert result.redacted_fields == ["prompt"]
