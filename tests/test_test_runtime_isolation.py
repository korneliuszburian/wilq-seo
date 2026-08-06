from __future__ import annotations

import os

from wilq.storage.local_state import DEFAULT_STATE_DB, state_db_path
from wilq.storage.metric_store import DEFAULT_METRIC_DB, metric_store_path


def test_pytest_session_uses_private_state_and_metric_paths() -> None:
    state_path = state_db_path()
    metric_path = metric_store_path()

    assert state_path != DEFAULT_STATE_DB
    assert metric_path != DEFAULT_METRIC_DB
    assert state_path.parent == metric_path.parent
    assert state_path.parent.name.startswith("wilq-pytest-state-")
    assert os.environ["WILQ_STATE_DB"] == str(state_path)
    assert os.environ["WILQ_METRIC_DB"] == str(metric_path)
