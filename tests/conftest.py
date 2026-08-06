"""Session-wide isolation for stateful WILQ tests."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from tests._contract_support.action_candidate_seed import save_action_candidate_metric_facts

_TEST_STATE_DIR = pytest.StashKey[Path]()


def pytest_configure(config: pytest.Config) -> None:
    root = Path(os.getenv("WILQ_TEST_TMPDIR", tempfile.gettempdir()))
    root.mkdir(parents=True, exist_ok=True)
    state_dir = Path(tempfile.mkdtemp(prefix="wilq-pytest-state-", dir=root))
    config.stash[_TEST_STATE_DIR] = state_dir
    os.environ["WILQ_STATE_DB"] = str(state_dir / "state.sqlite3")
    os.environ["WILQ_METRIC_DB"] = str(state_dir / "metrics.duckdb")
    save_action_candidate_metric_facts()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    del exitstatus
    shutil.rmtree(session.config.stash[_TEST_STATE_DIR], ignore_errors=True)
