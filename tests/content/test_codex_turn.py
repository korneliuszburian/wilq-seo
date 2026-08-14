import pytest
from pydantic import BaseModel, Field

from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content import codex_turn
from wilq.content.codex_turn import require_all_object_properties, runtime_trace
from wilq.content.drafts import draft_assurance, initial_full_draft_turn
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.planning import generated_proposal_turn
from wilq.content.quality import semantic_review_turn


class _ChildSchema(BaseModel):
    label: str = "domyślna"


class _TurnSchema(BaseModel):
    enabled: bool = True
    child: _ChildSchema = Field(default_factory=_ChildSchema)


def test_shared_schema_normalizer_matches_old_behavior() -> None:
    schema = _TurnSchema.model_json_schema()

    require_all_object_properties(schema)

    child = schema["$defs"]["_ChildSchema"]
    assert schema["required"] == ["enabled", "child"]
    assert child["required"] == ["label"]
    assert "default" not in schema["properties"]["enabled"]
    assert "default" not in child["properties"]["label"]


def test_shared_trace_mapper_preserves_event_and_usage() -> None:
    result = CodexAppServerTurnResult(
        status="completed",
        thread_id="thread-1",
        turn_id="turn-1",
        event_methods=("thread/started", "turn/completed"),
        item_types=("reasoning", "agentMessage"),
        external_call_attempted=True,
    )

    assert runtime_trace(result) == ContentCodexRuntimeTrace(
        status="completed",
        thread_id="thread-1",
        turn_id="turn-1",
        event_methods=["thread/started", "turn/completed"],
        item_types=["reasoning", "agentMessage"],
        external_call_attempted=True,
    )


def test_shared_mapping_raises_one_consistent_missing_key_message() -> None:
    with pytest.raises(RuntimeError, match="Codex output schema is missing"):
        codex_turn.mapping({}, "missing_key")
    with pytest.raises(RuntimeError, match="Codex output schema is missing"):
        codex_turn.properties({})
    with pytest.raises(RuntimeError, match="Codex output schema is missing"):
        codex_turn.definition({}, "missing")


def test_at_least_two_callers_use_the_shared_module() -> None:
    callers = (
        draft_assurance,
        initial_full_draft_turn,
        generated_proposal_turn,
        semantic_review_turn,
    )

    assert sum(
        getattr(caller, "require_all_object_properties", None)
        is codex_turn.require_all_object_properties
        for caller in callers
    ) >= 2
