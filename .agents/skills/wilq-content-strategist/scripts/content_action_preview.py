from __future__ import annotations

from typing import Any

CURRENT_CONTENT_URL_KEYS = frozenset(
    {"source_public_url", "final_canonical_url", "intended_final_url", "preview_url"}
)


def assert_current_content_url_keys(value: dict[str, Any], label: str) -> None:
    unexpected = sorted(
        key
        for key in value
        if (key.endswith("_url") or key.endswith("_host")) and key not in CURRENT_CONTENT_URL_KEYS
    )
    if unexpected:
        raise SystemExit(
            f"{label} exposes non-current content URL fields: " + ", ".join(unexpected)
        )


def _content_action(active_actions: Any, content_action_id: str) -> dict[str, Any]:
    if not isinstance(active_actions, list):
        raise SystemExit("Context pack active_action_objects must be a list")
    action = next(
        (
            item
            for item in active_actions
            if isinstance(item, dict) and item.get("id") == content_action_id
        ),
        None,
    )
    if not isinstance(action, dict):
        raise SystemExit(f"Context pack missing active {content_action_id}")
    payload = action.get("action_plan")
    if not isinstance(payload, dict):
        raise SystemExit("Content action plan must be an object")
    return payload


def _validate_url_contract(payload: dict[str, Any]) -> None:
    contract = payload.get("content_url_review_contract")
    summary = payload.get("content_url_review_summary")
    if isinstance(contract, dict):
        if contract.get("contract") != "content_url_preflight_review_v1":
            raise SystemExit("Content URL review contract has invalid version")
        if contract.get("scope") != "review_only":
            raise SystemExit("Content URL review contract must be review_only")
        if "wordpress_publish" not in set(contract.get("blocked_outputs") or []):
            raise SystemExit("Content URL review contract must block wordpress_publish")
    elif isinstance(summary, dict):
        if int(summary.get("required_fields_total") or 0) <= 0:
            raise SystemExit("Content URL review summary lacks required field count")
        if int(summary.get("allowed_outcomes_total") or 0) <= 0:
            raise SystemExit("Content URL review summary lacks allowed outcome count")
        if "URL" not in str(summary.get("next_step") or ""):
            raise SystemExit("Content URL review summary lacks readable next step")
    else:
        raise SystemExit("Content action lacks URL review contract or summary")
    assert_current_content_url_keys(payload, "Content action payload")


def _preview_items(payload: dict[str, Any], require_preview: bool) -> list[dict[str, Any]]:
    previews = payload.get("content_plan_items")
    if not require_preview and previews is None:
        return []
    if not isinstance(previews, list) or not previews:
        raise SystemExit("Content action lacks content_plan_items")
    if int(payload.get("content_plan_items_included") or 0) <= 0:
        raise SystemExit("Content action context omits content_plan_items")
    if not isinstance(previews[0], dict):
        raise SystemExit("Content brief preview must be an object")
    return [item for item in previews if isinstance(item, dict)]


def _validate_first_preview(preview: dict[str, Any]) -> None:
    if preview.get("apply_status_label") != "zablokowane do sprawdzenia":
        raise SystemExit("Content brief preview must keep apply blocked")
    if preview.get("write_status_label") != "bez zapisu automatycznego":
        raise SystemExit("Content brief preview must keep write blocked")
    if not preview.get("evidence_ids"):
        raise SystemExit("Content brief preview lacks evidence IDs")
    if "gwarancja pozycji" not in set(preview.get("blocked_claim_labels") or []):
        raise SystemExit("Content brief preview must block gwarancja pozycji claims")
    for field in (
        "intent",
        "content_angle",
        "audience",
        "h1_direction",
        "seo_title_direction",
        "meta_description_direction",
        "schema_direction",
        "cta_direction",
        "content_gate_summary",
    ):
        if not str(preview.get(field) or "").strip():
            raise SystemExit(f"Content brief preview lacks {field}")
    for field in (
        "key_objections",
        "h2_direction",
        "faq_direction",
        "internal_link_direction",
        "source_facts",
        "missing_evidence",
        "blocked_claim_labels",
        "legal_review_notes",
        "brand_voice_notes",
        "required_check_labels",
    ):
        if not isinstance(preview.get(field), list) or not preview[field]:
            raise SystemExit(f"Content brief preview lacks {field}")


def _validate_gates(preview: dict[str, Any]) -> None:
    blockers = preview.get("publication_blocker_labels")
    if (not isinstance(blockers, list) or not blockers) and int(
        preview.get("publication_blockers_total") or 0
    ) <= 0:
        raise SystemExit("Content brief preview lacks publication blocker labels")
    for field in ("source_public_url", "final_canonical_url", "intended_final_url"):
        if field not in preview:
            raise SystemExit(f"Content brief preview lacks {field}")
    if "ekologus.dev.proudsite.pl" in str(preview.get("final_canonical_url") or ""):
        raise SystemExit("Content brief preview final_canonical_url must not point to dev preview")
    requirements = preview.get("required_check_labels") or []
    if not any("duplikacji" in str(item) for item in requirements):
        raise SystemExit(
            "Content brief preview required_check_labels must include duplicate review"
        )


def _validate_gsc_preview(previews: list[dict[str, Any]]) -> None:
    preview = next((item for item in previews if item.get("source_type") == "gsc_query_page"), None)
    if preview is None:
        return
    for field in (
        "source_public_url",
        "final_canonical_url",
        "intended_final_url",
        "inventory_gate_status",
        "canonical_gate_status",
        "duplicate_gate_status",
    ):
        if not str(preview.get(field) or "").strip():
            raise SystemExit(f"GSC content brief preview lacks {field}")
    if "ekologus.dev.proudsite.pl" in str(preview.get("final_canonical_url") or ""):
        raise SystemExit("GSC content brief final_canonical_url must not point to dev preview")


def _preview_summary(preview: dict[str, Any]) -> dict[str, Any]:
    return {
        "topic": preview.get("topic"),
        "source_type": preview.get("source_type"),
        "content_angle": preview.get("content_angle"),
        "intent": preview.get("intent"),
        "audience": preview.get("audience"),
        "key_objections_label": "obiekcje",
        "key_objections": (preview.get("key_objections") or [])[:4],
        "h1_direction": preview.get("h1_direction"),
        "seo_title_direction": preview.get("seo_title_direction"),
        "meta_description_direction": preview.get("meta_description_direction"),
        "h2_direction": (preview.get("h2_direction") or [])[:4],
        "faq_direction": (preview.get("faq_direction") or [])[:4],
        "schema_direction": preview.get("schema_direction"),
        "inventory_gate_status": preview.get("inventory_gate_status"),
        "canonical_gate_status": preview.get("canonical_gate_status"),
        "duplicate_gate_status": preview.get("duplicate_gate_status"),
        "content_gate_summary": preview.get("content_gate_summary"),
        "cta_direction": preview.get("cta_direction"),
        "publication_readiness_status": preview.get("publication_readiness_status"),
        "publication_blockers": (preview.get("publication_blockers") or [])[:6],
        "source_facts_label": "fakty źródłowe",
        "source_facts": (preview.get("source_facts") or [])[:4],
        "missing_evidence": (preview.get("missing_evidence") or [])[:3],
        "blocked_claim_labels": (preview.get("blocked_claim_labels") or [])[:6],
        "source_public_url": preview.get("source_public_url"),
        "final_canonical_url": preview.get("final_canonical_url"),
        "intended_final_url": preview.get("intended_final_url"),
        "preview_url": preview.get("preview_url"),
        "evidence_ids": (preview.get("evidence_ids") or [])[:5],
    }


def validate_content_action_preview(
    active_actions: Any, *, content_action_id: str, require_preview: bool
) -> list[dict[str, Any]]:
    payload = _content_action(active_actions, content_action_id)
    _validate_url_contract(payload)
    previews = _preview_items(payload, require_preview)
    if not previews:
        return []
    _validate_first_preview(previews[0])
    _validate_gates(previews[0])
    for preview in previews:
        assert_current_content_url_keys(preview, "Content context-pack preview")
    _validate_gsc_preview(previews)
    return [_preview_summary(preview) for preview in previews[:3]]
