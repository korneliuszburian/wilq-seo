from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from scripts.test_backend_shard import (
    discover_backend_tests,
    parse_shard,
    select_shard,
)

ROOT = Path(__file__).resolve().parents[1]


def test_backend_shards_are_complete_disjoint_and_reject_invalid_coordinates() -> None:
    discovered = discover_backend_tests(ROOT)
    shards = [set(select_shard(discovered, index=index, total=8)) for index in range(1, 9)]

    assert discovered
    assert set().union(*shards) == set(discovered)
    assert sum(len(shard) for shard in shards) == len(discovered)

    for invalid in ("0/8", "9/8", "1/0", "wat"):
        with pytest.raises(argparse.ArgumentTypeError):
            parse_shard(invalid)
