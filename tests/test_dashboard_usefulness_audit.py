from __future__ import annotations

from scripts.dashboard_usefulness_audit import SurfaceSpec, evaluate_surface


def _spec() -> SurfaceSpec:
    return SurfaceSpec(
        "fixture",
        "/fixture",
        "Fixture",
        "diagnostic",
        "production",
        "/api/fixture",
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
    )


def _payload(**extra: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "evidence_ids": ["ev_fixture"],
        "source_connectors": ["fixture"],
        "action_ids": ["act_fixture"],
        "decision_queue": [{"next_step": "Sprawdź fixture."}],
        "blocked_claims": ["nie obiecuj wyniku"],
        "next_step": "Sprawdź fixture.",
    }
    payload.update(extra)
    return payload


def test_dashboard_audit_honors_explicit_blocked_api_status() -> None:
    report = evaluate_surface(_spec(), {"payload": _payload(status="blocked"), "errors": []})

    assert report["usefulness_score"] == 10
    assert report["semantic_readiness"] == "blocked"
    assert report["readiness"] == "blocked"


def test_dashboard_audit_honors_review_required_production_depth() -> None:
    report = evaluate_surface(
        _spec(),
        {
            "payload": _payload(
                production_depth_readiness={
                    "status": "source_backed_review_required",
                    "ready_for_daily_content": False,
                }
            ),
            "errors": [],
        },
    )

    assert report["semantic_readiness"] == "review_ready"
    assert report["readiness"] == "review_ready"


def test_dashboard_audit_keeps_ready_surface_demo_ready() -> None:
    report = evaluate_surface(_spec(), {"payload": _payload(status="ready"), "errors": []})

    assert report["semantic_readiness"] is None
    assert report["readiness"] == "demo_ready"
