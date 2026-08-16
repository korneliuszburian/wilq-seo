from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel


def model_json(value: BaseModel | Mapping[str, Any]) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
