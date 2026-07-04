from __future__ import annotations

from typing import Any


def compact_preview_card_for_skill_context(card: dict[str, Any]) -> dict[str, Any]:
    compact = dict(card)
    compact.pop("id", None)
    rows = compact.get("rows")
    if isinstance(rows, list):
        compact["rows_total"] = len(rows)
        compact["rows"] = rows[:6]
        compact["rows_included"] = len(compact["rows"])
    return compact


def _compact_ngram_preview_for_context(preview_items: list[Any]) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "id",
        "ngram",
        "ngram_size",
        "source_search_term_count",
        "sample_search_terms",
        "clicks",
        "impressions",
        "cost_micros",
        "conversions",
        "conversion_value",
        "operation_type",
        "required_validation",
        "blocked_claims",
        "evidence_ids",
        "api_mutation_ready",
        "apply_allowed",
        "destructive",
    }
    for item in preview_items[:1]:
        if not isinstance(item, dict):
            continue
        compact_item = {key: item.get(key) for key in keep_keys if key in item}
        sample_search_terms = compact_item.get("sample_search_terms")
        if isinstance(sample_search_terms, list):
            compact_item["sample_search_terms"] = sample_search_terms[:1]
        evidence_ids = compact_item.get("evidence_ids")
        if isinstance(evidence_ids, list):
            compact_item["evidence_ids"] = evidence_ids[:1]
        required_validation = compact_item.get("required_validation")
        if isinstance(required_validation, list):
            compact_item["required_validation_total"] = len(required_validation)
            compact_item["required_validation"] = required_validation[:2]
        blocked_claims = compact_item.get("blocked_claims")
        if isinstance(blocked_claims, list):
            compact_item["blocked_claims"] = blocked_claims[:2]
        compact_items.append(compact_item)
    return compact_items


def _compact_ga4_tracking_preview_for_context(preview_items: list[Any]) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "id",
        "preview_contract",
        "operation_type",
        "landing_page",
        "source_medium",
        "campaign_name",
        "tracking_dimension_gaps",
        "metric_snapshot",
        "metric_snapshot_labels",
        "reason",
        "required_validation",
        "blocked_claims",
        "evidence_ids",
        "api_mutation_ready",
        "apply_allowed",
        "destructive",
    }
    for item in preview_items[:3]:
        if isinstance(item, dict):
            compact_items.append({key: item[key] for key in keep_keys if key in item})
    return compact_items


def _compact_localo_visibility_preview_for_context(
    preview_items: list[Any],
) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "id",
        "preview_contract",
        "operation_type",
        "metric_snapshot",
        "allowed_contracts",
        "missing_read_contracts",
        "reason",
        "required_validation",
        "blocked_claims",
        "evidence_ids",
        "api_mutation_ready",
        "apply_allowed",
        "destructive",
    }
    for item in preview_items[:1]:
        if not isinstance(item, dict):
            continue
        compact_item = {key: item[key] for key in keep_keys if key in item}
        metric_snapshot = compact_item.get("metric_snapshot")
        if isinstance(metric_snapshot, dict):
            compact_item["metric_snapshot"] = dict(list(metric_snapshot.items())[:12])
        required_validation = compact_item.get("required_validation")
        if isinstance(required_validation, list):
            compact_item["required_validation_total"] = len(required_validation)
            compact_item["required_validation"] = required_validation[:4]
        blocked_claims = compact_item.get("blocked_claims")
        if isinstance(blocked_claims, list):
            compact_item["blocked_claims"] = blocked_claims[:5]
        evidence_ids = compact_item.get("evidence_ids")
        if isinstance(evidence_ids, list):
            compact_item["evidence_ids"] = evidence_ids[:3]
        compact_items.append(compact_item)
    return compact_items


def compact_content_brief_preview_for_context(
    preview_items: list[Any],
) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "candidate_id",
        "source_type",
        "source_type_label",
        "mode",
        "mode_label",
        "topic",
        "source_public_url",
        "preview_url",
        "intended_final_url",
        "final_canonical_url",
        "inventory_gate_status",
        "inventory_gate_status_label",
        "canonical_gate_status",
        "canonical_gate_status_label",
        "duplicate_gate_status",
        "duplicate_gate_status_label",
        "content_gate_summary",
        "competitor_domain",
        "wordpress_inventory_match",
        "wordpress_inventory_match_label",
        "gsc_demand",
        "metric_snapshot",
        "metric_snapshot_labels",
        "brief_goal",
        "intent",
        "content_angle",
        "audience",
        "key_objections",
        "h1_direction",
        "seo_title_direction",
        "meta_description_direction",
        "h2_direction",
        "faq_direction",
        "schema_direction",
        "cta_direction",
        "internal_link_direction",
        "legal_review_notes",
        "brand_voice_notes",
        "publication_readiness_status",
        "publication_readiness_status_label",
        "publication_blockers",
        "publication_blocker_labels",
        "source_facts",
        "missing_evidence",
        "forbidden_claims",
        "decision_option_labels",
        "required_validation",
        "required_validation_labels",
        "blocked_claims",
        "blocked_claim_labels",
        "source_connectors",
        "evidence_ids",
        "apply_allowed",
        "api_mutation_ready",
        "destructive",
    }
    for item in preview_items[:4]:
        if isinstance(item, dict):
            compact_item = {key: item[key] for key in keep_keys if key in item}
            if compact_item.get("source_type") == "ahrefs_gap_review":
                compact_item.pop("metric_snapshot", None)
                compact_item.pop("metric_snapshot_labels", None)
            for key, limit in (
                ("key_objections", 3),
                ("h2_direction", 4),
                ("faq_direction", 4),
                ("internal_link_direction", 3),
                ("legal_review_notes", 4),
                ("brand_voice_notes", 4),
                ("publication_blockers", 6),
                ("source_facts", 4),
                ("missing_evidence", 3),
                ("forbidden_claims", 5),
                ("required_validation", 4),
                ("blocked_claims", 5),
                ("source_connectors", 4),
                ("evidence_ids", 3),
            ):
                value = compact_item.get(key)
                if isinstance(value, list):
                    values = value[:limit]
                    if key == "source_facts":
                        values = compact_content_source_facts_for_context(values)
                    compact_item[key] = values
                    compact_item[f"{key}_total"] = len(value)
            compact_items.append(compact_item)
    return compact_items


def compact_content_source_facts_for_context(values: list[Any]) -> list[Any]:
    compact_values: list[Any] = []
    for value in values:
        if isinstance(value, str) and value.startswith("Strona z GSC:"):
            compact_values.append("Strona z GSC: publiczny adres strony")
        elif isinstance(value, str) and value.startswith("metric_name=ahrefs_"):
            compact_values.append("Metryka Ahrefs: sygnał luki do ręcznego review")
        else:
            compact_values.append(value)
    return compact_values


def compact_wordpress_draft_payload_preview_for_context(
    preview_items: list[Any],
) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "preview_contract",
        "source_preview_contract",
        "candidate_id",
        "source_type",
        "source_type_label",
        "mode",
        "mode_label",
        "operation_type",
        "operation_type_label",
        "post_status",
        "post_status_label",
        "topic",
        "intent",
        "source_public_url",
        "preview_url",
        "intended_final_url",
        "final_canonical_url",
        "inventory_gate_status",
        "inventory_gate_status_label",
        "canonical_gate_status",
        "canonical_gate_status_label",
        "duplicate_gate_status",
        "duplicate_gate_status_label",
        "content_gate_summary",
        "draft_generation_status",
        "draft_generation_status_label",
        "draft_blockers",
        "draft_blocker_labels",
        "draft_generation_summary",
        "draft_generation_contract",
        "draft_readiness_review_contract",
        "draft_readiness_review_contract_summary",
        "draft_readiness_review_recorded_outcome",
        "draft_readiness_review_summary",
        "canonical_review_recorded_outcome",
        "duplicate_review_recorded_outcome",
        "legal_factual_review_recorded_outcome",
        "human_review_recorded_outcome",
        "wordpress_draft_handoff_status",
        "wordpress_draft_handoff_blockers",
        "wordpress_draft_handoff_blocker_labels",
        "wordpress_draft_handoff_summary",
        "wordpress_draft_handoff_contract",
        "wordpress_draft_handoff_contract_summary",
        "post_publication_measurement_plan",
        "post_publication_measurement_summary",
        "required_validation",
        "required_validation_labels",
        "blocked_claims",
        "blocked_claim_labels",
        "source_connectors",
        "evidence_ids",
        "mutation_allowed",
        "apply_allowed",
        "api_mutation_ready",
        "destructive",
    }
    for item in preview_items[:2]:
        if not isinstance(item, dict):
            continue
        compact_item = {key: item[key] for key in keep_keys if key in item}
        draft_generation_contract = compact_item.get("draft_generation_contract")
        if isinstance(draft_generation_contract, dict):
            for key, limit in (
                ("blocked_until", 6),
                ("requires_passed_gates", 7),
                ("output_must_include", 10),
                ("forbidden_outputs", 6),
            ):
                value = draft_generation_contract.get(key)
                if isinstance(value, list):
                    draft_generation_contract[key] = value[:limit]
                    draft_generation_contract[f"{key}_total"] = len(value)
        draft_readiness_contract = compact_item.get("draft_readiness_review_contract")
        if isinstance(draft_readiness_contract, dict):
            for key, limit in (
                ("allowed_outcomes", 5),
                ("required_fields", 7),
                ("blocked_outputs", 6),
            ):
                value = draft_readiness_contract.get(key)
                if isinstance(value, list):
                    draft_readiness_contract[key] = value[:limit]
                    draft_readiness_contract[f"{key}_total"] = len(value)
        wordpress_draft_handoff_contract = compact_item.get("wordpress_draft_handoff_contract")
        if isinstance(wordpress_draft_handoff_contract, dict):
            for key, limit in (
                ("blocked_until", 7),
                ("requires_passed_gates", 7),
                ("blocked_outputs", 5),
            ):
                value = wordpress_draft_handoff_contract.get(key)
                if isinstance(value, list):
                    wordpress_draft_handoff_contract[key] = value[:limit]
                    wordpress_draft_handoff_contract[f"{key}_total"] = len(value)
        compact_post_publication_measurement_plan(compact_item)
        draft_payload = item.get("draft_payload")
        if isinstance(draft_payload, dict):
            compact_item["draft_payload"] = {
                key: draft_payload[key]
                for key in (
                    "post_status",
                    "post_title",
                    "post_excerpt_direction",
                )
                if key in draft_payload
            }
            content_blocks = draft_payload.get("content_blocks")
            if isinstance(content_blocks, list):
                compact_item["draft_payload"]["content_blocks_total"] = len(content_blocks)
                compact_item["draft_payload"]["content_blocks"] = [
                    block for block in content_blocks[:4] if isinstance(block, dict)
                ]
                compact_item["draft_payload"]["content_blocks_included"] = len(
                    compact_item["draft_payload"]["content_blocks"]
                )
        compact_items.append(compact_item)
    return compact_items


def _compact_wordpress_draft_handoff_preview_for_context(
    preview_items: list[Any],
) -> list[dict[str, Any]]:
    compact_items: list[dict[str, Any]] = []
    keep_keys = {
        "preview_contract",
        "operation_type",
        "candidate_id",
        "topic",
        "source_public_url",
        "preview_url",
        "intended_final_url",
        "final_canonical_url",
        "canonical_gate_status",
        "duplicate_gate_status",
        "wordpress_draft_handoff_status",
        "required_next_action_contract",
        "post_publication_measurement_plan",
        "required_validation",
        "blocked_claims",
        "apply_allowed",
        "api_mutation_ready",
        "destructive",
    }
    for item in preview_items[:4]:
        if not isinstance(item, dict):
            continue
        compact_item = {key: item[key] for key in keep_keys if key in item}
        for key, limit in (
            ("required_validation", 6),
            ("blocked_claims", 5),
        ):
            value = compact_item.get(key)
            if isinstance(value, list):
                compact_item[key] = value[:limit]
                compact_item[f"{key}_total"] = len(value)
        compact_post_publication_measurement_plan(compact_item)
        compact_items.append(compact_item)
    return compact_items


def compact_post_publication_measurement_plan(item: dict[str, Any]) -> None:
    measurement_plan = item.get("post_publication_measurement_plan")
    if not isinstance(measurement_plan, dict):
        return
    keep_keys = {
        "contract_version",
        "scope",
        "final_canonical_url",
        "status",
        "baseline_window",
        "followup_windows",
        "required_source_connectors",
        "required_metric_groups",
        "requires_before_claims",
        "blocked_outputs",
    }
    compact_plan = {key: measurement_plan[key] for key in keep_keys if key in measurement_plan}
    for key, limit in (
        ("followup_windows", 3),
        ("required_source_connectors", 3),
        ("required_metric_groups", 3),
        ("requires_before_claims", 5),
        ("blocked_outputs", 5),
    ):
        value = compact_plan.get(key)
        if isinstance(value, list):
            compact_plan[key] = value[:limit]
            compact_plan[f"{key}_total"] = len(value)
    item["post_publication_measurement_plan"] = compact_plan
