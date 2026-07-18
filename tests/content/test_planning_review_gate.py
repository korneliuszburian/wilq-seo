from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from apps.api.wilq_api.routers.content_workflow import _require_generated_section_map


def test_section_map_review_rejects_baseline_plan() -> None:
    with pytest.raises(HTTPException, match="baseline") as error:
        _require_generated_section_map(
            SimpleNamespace(generation_status="baseline", proposal_id=None)
        )

    assert error.value.status_code == 409


def test_section_map_review_accepts_persisted_generated_plan() -> None:
    _require_generated_section_map(
        SimpleNamespace(generation_status="codex_generated", proposal_id="proposal_1")
    )
