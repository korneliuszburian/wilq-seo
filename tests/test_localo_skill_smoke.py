from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def load_localo_smoke() -> ModuleType:
    module_path = Path(".agents/skills/wilq-localo-operator/scripts/smoke_skill_contract.py")
    spec = importlib.util.spec_from_file_location("localo_skill_smoke", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def localo_context_pack() -> dict[str, Any]:
    return {
        "strict_instruction": "Codex must not invent metrics; fetch WILQ API evidence first.",
        "connector_status": [],
        "evidence_summaries": [{"id": "ev_refresh_refresh_localo_completed"}],
        "top_opportunities": [],
        "connector_refresh_runs": [
            {
                "id": "refresh_localo_failed_after_completed",
                "connector_id": "localo",
                "status": "failed",
                "metric_summary": {"api": "localo_mcp_oauth_probe"},
            }
        ],
        "active_action_objects": [
            {
                "id": "act_review_localo_visibility_facts",
                "payload": {
                    "payload_preview": [
                        {
                            "preview_contract": "local_visibility_review_preview_v1",
                            "apply_allowed": False,
                            "api_mutation_ready": False,
                            "metric_snapshot": {"localo_reviews_count": 798},
                        }
                    ]
                },
            }
        ],
        "localo_diagnostics": {
            "evidence_ids": ["ev_refresh_refresh_localo_completed"],
            "access_probe": {"status": "access_ready"},
            "latest_refresh": {
                "id": "refresh_localo_completed",
                "connector_id": "localo",
                "status": "completed",
                "metric_summary": {
                    "api": "localo_mcp_oauth_probe",
                    "mcp_initialize_status": 200,
                    "localo_read_contract_count": 5,
                },
            },
            "decision_queue": [
                {
                    "id": "localo_review_visibility_facts",
                    "allowed_evidence": [
                        "place_inventory",
                        "local_rankings",
                        "gbp_visibility",
                        "competitor_visibility",
                        "reviews",
                    ],
                    "missing_read_contracts": ["local_tasks"],
                    "blocked_claims": ["poprawa widoczności lokalnej"],
                    "metric_facts": [{"name": "localo_reviews_count", "value": 798}],
                },
                {
                    "id": "localo_block_visibility_claims_without_read_contract",
                    "metric_facts": [],
                },
            ],
        },
    }


def test_localo_smoke_uses_diagnostics_without_refresh_by_default(
    monkeypatch: Any,
) -> None:
    module = load_localo_smoke()
    calls: list[tuple[str, str]] = []

    def fake_request_json(
        api_base: str,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> Any:
        del api_base, body
        calls.append((method, path))
        if path == "/api/connectors/localo/refresh":
            raise AssertionError("Default Localo smoke must not force vendor refresh")
        if path == "/api/health":
            return {"status": "ok"}
        if path == "/api/codex/context-pack":
            return localo_context_pack()
        if path == "/api/marketing/brief":
            return {"sections": []}
        if path == "/api/connectors/localo/status":
            return {
                "id": "localo",
                "status": "configured",
                "configured": True,
                "missing_credentials": [],
                "error": None,
            }
        if path == "/api/actions/act_review_localo_visibility_facts/validate":
            return {
                "action_id": "act_review_localo_visibility_facts",
                "valid": True,
                "status": "valid",
                "errors": [],
            }
        raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(module, "request_json", fake_request_json)
    monkeypatch.setattr(
        sys,
        "argv",
        ["smoke_skill_contract.py", "--api-base", "http://127.0.0.1:8000"],
    )

    assert module.main() == 0
    assert ("POST", "/api/connectors/localo/refresh") not in calls
