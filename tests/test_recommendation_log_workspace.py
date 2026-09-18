from __future__ import annotations

import pytest

from wilq.audit.identity import LOCAL_PILOT_AUDIT_IDENTITY
from wilq.briefing.recommendation_log import assert_active_recommendation_workspace


def test_canonical_workspace_is_accepted() -> None:
    assert_active_recommendation_workspace(LOCAL_PILOT_AUDIT_IDENTITY.workspace_id)


@pytest.mark.parametrize("workspace_id", ["ekologus", "", "other_workspace"])
def test_non_canonical_workspace_is_rejected(workspace_id: str) -> None:
    with pytest.raises(ValueError):
        assert_active_recommendation_workspace(workspace_id)
