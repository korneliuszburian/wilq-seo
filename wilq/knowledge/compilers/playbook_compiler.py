from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from wilq.knowledge.cards import seed_cards
from wilq.schemas import KnowledgeCard, KnowledgeCompilerResult, MarketingPlaybook

PLAYBOOK_ROOT = Path(__file__).resolve().parents[1] / "playbooks"
PLAYBOOK_FILE = PLAYBOOK_ROOT / "marketing_playbooks.yaml"


def _yaml_safe_load(path: Path) -> dict[str, Any]:
    yaml_module = import_module("yaml")
    safe_load = cast(Callable[[str], Any], yaml_module.__dict__["safe_load"])
    loaded = safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Playbook file must contain a mapping: {path}")
    return cast(dict[str, Any], loaded)


@lru_cache(maxsize=1)
def list_playbooks() -> tuple[MarketingPlaybook, ...]:
    loaded = _yaml_safe_load(PLAYBOOK_FILE)
    playbook_data = loaded.get("playbooks")
    if not isinstance(playbook_data, list):
        raise ValueError(f"Playbook file requires playbooks list: {PLAYBOOK_FILE}")
    source_path = str(PLAYBOOK_FILE.relative_to(PLAYBOOK_ROOT.parents[2]))
    playbooks: list[MarketingPlaybook] = []
    for item in playbook_data:
        if not isinstance(item, dict):
            raise ValueError(f"Playbook item must be a mapping: {PLAYBOOK_FILE}")
        playbooks.append(MarketingPlaybook.model_validate({**item, "source_path": source_path}))
    return tuple(playbooks)


def get_playbook(playbook_id: str) -> MarketingPlaybook | None:
    return next((playbook for playbook in list_playbooks() if playbook.id == playbook_id), None)


def compile_playbook_cards() -> list[KnowledgeCard]:
    cards = [
        KnowledgeCard(
            id=f"card_{playbook.id}",
            card_type=playbook.card_type,
            title=playbook.title,
            summary=playbook.compact_playbook,
            source_type="marketing_playbook",
            source_id=playbook.id,
            source_url_or_path=playbook.source_path,
            confidence=0.86,
            source_lineage=[
                playbook.source_path,
                *playbook.source_anchors,
                *playbook.expert_rule_ids,
            ],
        )
        for playbook in list_playbooks()
    ]
    return [*seed_cards(), *cards]


def condense_playbooks() -> KnowledgeCompilerResult:
    cards = compile_playbook_cards()
    return KnowledgeCompilerResult(status="completed", card_count=len(cards), cards=cards)
