from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from wilq.schemas import ExpertCapability, ExpertRule, ExpertRuleSummary, PlatformTrapContract

EXPERT_ROOT = Path(__file__).resolve().parent

EXPERT_SOURCE_ID_BY_DOMAIN = {
    "ads": "src_google_ads_api_docs",
    "analytics": "src_ga4_data_api_docs",
    "merchant": "src_google_merchant_center_docs",
    "seo": "src_google_search_console_docs",
    "wordpress": "src_wordpress_rest_docs",
    "content": "src_wilq_content_rules",
    "local": "src_localo_and_gbp_rules",
    "social": "src_social_platform_review_rules",
}


def _yaml_safe_load(path: Path) -> dict[str, Any]:
    yaml_module = import_module("yaml")
    safe_load = cast(Callable[[str], Any], yaml_module.__dict__["safe_load"])
    loaded = safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Expert rule file must contain a mapping: {path}")
    return cast(dict[str, Any], loaded)


def _required_string(data: dict[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expert rule {path} requires non-empty {key}.")
    return value


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expert rule field {key} must be a non-empty string when present.")
    return value


def _string_list(data: dict[str, Any], key: str, path: Path) -> list[str]:
    value = data.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"Expert rule {path} field {key} must be a list of non-empty strings.")
    return cast(list[str], value)


def _requires_evidence(required_inputs: list[str], required_mapping: list[str]) -> bool:
    joined = required_inputs + required_mapping
    return any("evidence" in item for item in joined)


def _platform_trap(data: dict[str, Any], path: Path) -> PlatformTrapContract | None:
    value = data.get("platform_trap")
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"Expert rule {path} field platform_trap must be a mapping.")
    try:
        return PlatformTrapContract.model_validate(value)
    except ValueError as exc:
        raise ValueError(f"Expert rule {path} has an invalid platform_trap contract.") from exc


def _load_rule(path: Path) -> ExpertRule:
    data = _yaml_safe_load(path)
    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ValueError(f"Expert rule {path} requires integer version.")

    required_inputs = _string_list(data, "required_inputs", path)
    required_mapping = _string_list(data, "required_mapping", path)
    platform_trap = _platform_trap(data, path)
    return ExpertRule(
        id=_required_string(data, "id", path),
        name=_required_string(data, "name", path),
        domain=path.parent.name,
        version=version,
        source_anchor=_required_string(data, "source_anchor", path),
        source_path=str(path.relative_to(EXPERT_ROOT.parent.parent)),
        when_to_use=_optional_string(data, "when_to_use"),
        required_inputs=required_inputs,
        diagnostic_logic=_string_list(data, "diagnostic_logic", path),
        recommended_actions=_string_list(data, "recommended_actions", path),
        risk_notes=_optional_string(data, "risk_notes"),
        output_contract=_required_string(data, "output_contract", path),
        capabilities=_string_list(data, "capabilities", path),
        required_mapping=required_mapping,
        source_ids=[
            EXPERT_SOURCE_ID_BY_DOMAIN.get(
                path.parent.name,
                f"src_wilq_{path.parent.name}_rules",
            )
        ],
        requires_evidence=_requires_evidence(required_inputs, required_mapping),
        condition=_optional_string(data, "condition"),
        required_connectors=_string_list(data, "required_connectors", path),
        required_metrics=_string_list(data, "required_metrics", path),
        minimum_window=_optional_string(data, "minimum_window"),
        segmentation=_string_list(data, "segmentation", path),
        false_positive_checks=_string_list(data, "false_positive_checks", path),
        blocked_states=_string_list(data, "blocked_states", path),
        recommendation_template=_optional_string(data, "recommendation_template"),
        forbidden_conclusions=_string_list(data, "forbidden_conclusions", path),
        safety_level=data.get("safety_level", "medium"),
        eval_case_ids=_string_list(data, "eval_case_ids", path),
        platform_trap=platform_trap,
    )


@lru_cache(maxsize=1)
def list_expert_rules() -> tuple[ExpertRule, ...]:
    return tuple(_load_rule(path) for path in sorted(EXPERT_ROOT.glob("*/*.yaml")))


def get_expert_rule(rule_id: str) -> ExpertRule | None:
    return next((rule for rule in list_expert_rules() if rule.id == rule_id), None)


def list_expert_rule_summaries(limit: int | None = None) -> list[ExpertRuleSummary]:
    summaries = [
        ExpertRuleSummary(
            id=rule.id,
            name=rule.name,
            domain=rule.domain,
            source_anchor=rule.source_anchor,
            required_inputs=rule.required_inputs,
            recommended_actions=rule.recommended_actions,
            source_ids=rule.source_ids,
            output_contract=rule.output_contract,
            requires_evidence=rule.requires_evidence,
            condition=rule.condition,
            required_connectors=rule.required_connectors,
            required_metrics=rule.required_metrics,
            minimum_window=rule.minimum_window,
            segmentation=rule.segmentation,
            false_positive_checks=rule.false_positive_checks,
            blocked_states=rule.blocked_states,
            recommendation_template=rule.recommendation_template,
            forbidden_conclusions=rule.forbidden_conclusions,
            safety_level=rule.safety_level,
            eval_case_ids=rule.eval_case_ids,
            platform_trap=rule.platform_trap,
        )
        for rule in list_expert_rules()
    ]
    if limit is None:
        return summaries
    return summaries[:limit]


def list_expert_capabilities() -> list[ExpertCapability]:
    capabilities: list[ExpertCapability] = []
    for rule in list_expert_rules():
        for capability in rule.capabilities:
            capabilities.append(
                ExpertCapability(
                    id=capability,
                    domain=rule.domain,
                    source_rule_id=rule.id,
                    required_mapping=rule.required_mapping,
                    output_contract=rule.output_contract,
                    requires_evidence=rule.requires_evidence,
                )
            )
    return capabilities
