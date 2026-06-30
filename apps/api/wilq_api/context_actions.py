from __future__ import annotations

from typing import Any

from apps.api.wilq_api.context_scopes import SKILL_ACTION_ID_SCOPES
from wilq.actions.service import list_actions
from wilq.briefing.marketing_brief import core_brief_actions
from wilq.schemas import ActionObject


def full_context_actions_for_skill(skill: str | None) -> list[ActionObject]:
    actions = list_actions()
    if skill == "wilq-daily-command":
        return core_brief_actions(actions)
    return actions


def skill_context_actions_for_skill(
    skill: str,
    actions: list[ActionObject],
    diagnostics: dict[str, Any],
) -> list[ActionObject]:
    actions = stateful_context_actions(skill, actions, diagnostics)
    return actions_for_skill_scope(skill, actions)


def stateful_context_actions(
    skill: str,
    actions: list[ActionObject],
    diagnostics: dict[str, Any],
) -> list[ActionObject]:
    ads_diagnostics = diagnostics.get("ads_diagnostics")
    if (
        skill in {"wilq-ads-doctor", "wilq-custom-segments", "wilq-campaign-builder"}
        and isinstance(ads_diagnostics, dict)
        and ads_diagnostics.get("live_data_available") is True
    ):
        return [action for action in actions if action.id != "act_configure_google_ads_env"]
    return actions


def actions_for_skill_scope(skill: str, actions: list[ActionObject]) -> list[ActionObject]:
    if skill not in SKILL_ACTION_ID_SCOPES:
        return actions
    allowed_action_ids = SKILL_ACTION_ID_SCOPES[skill]
    return [action for action in actions if action.id in allowed_action_ids]


def actions_for_scope(
    actions: list[ActionObject],
    scoped_connectors: set[str],
) -> list[ActionObject]:
    return [action for action in actions if action.connector in scoped_connectors]
