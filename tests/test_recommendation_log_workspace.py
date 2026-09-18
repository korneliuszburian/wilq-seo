from __future__ import annotations

import pytest

from wilq.briefing.recommendation_log import assert_active_recommendation_workspace


def test_active_product_workspace_is_accepted() -> None:
    assert_active_recommendation_workspace("ekologus")


@pytest.mark.parametrize("workspace_id", ["ekologus_local_pilot", "", "other_workspace"])
def test_other_workspace_is_rejected(workspace_id: str) -> None:
    with pytest.raises(ValueError):
        assert_active_recommendation_workspace(workspace_id)
