from __future__ import annotations

from typing import Any

KEYWORD_PLANNER_ACCESS_ACTION_ID = "act_configure_google_ads_keyword_planner_access"
KEYWORD_PLANNER_ACCESS_ACTION_TYPE = "configure_google_ads_keyword_planner_access"
KEYWORD_PLANNER_ACCESS_BLOCKED_CLAIMS = [
    "audience size",
    "forecast",
    "conversion uplift",
    "ROAS",
    "targeting applied",
    "campaign performance",
]


def keyword_planner_access_payload(blocker: str) -> dict[str, Any]:
    return {
        "action_type": KEYWORD_PLANNER_ACCESS_ACTION_TYPE,
        "connector": "google_ads",
        "mode": "prepare_only",
        "blocked_api": "Keyword Planner",
        "blocked_reason": blocker,
        "required_google_ads_state": [
            "developer_token_approved_for_keyword_planner",
            "keyword_planner_generate_ideas_allowed",
        ],
        "helper_steps": [
            "Sprawdź status tokena deweloperskiego Google Ads API w Google Ads API Center.",
            (
                "Jeśli token jest w Basic Access albo niezatwierdzony, przejdź proces "
                "akceptacji Google przed procesem prognozy i wzbogacania."
            ),
            (
                "Po zmianie statusu wykonaj ponowny odczyt danych Google Ads przez WILQ CLI "
                "i potwierdź, że Keyword Planner zwraca wiersze pomysłów."
            ),
        ],
        "required_validation": [
            "confirm_developer_token_approval",
            "rerun_google_ads_data_read",
            "verify_keyword_planner_idea_rows",
            "human_confirm_before_apply",
        ],
        "blocked_claims": KEYWORD_PLANNER_ACCESS_BLOCKED_CLAIMS,
        "apply_allowed": False,
        "destructive": False,
    }


def validate_keyword_planner_access_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("connector") != "google_ads":
        errors.append("configure_google_ads_keyword_planner_access requires connector=google_ads.")
    if payload.get("mode") != "prepare_only":
        errors.append("configure_google_ads_keyword_planner_access requires mode=prepare_only.")
    if payload.get("blocked_api") != "Keyword Planner":
        errors.append("configure_google_ads_keyword_planner_access requires blocked_api.")
    if not isinstance(payload.get("blocked_reason"), str) or not payload["blocked_reason"].strip():
        errors.append("configure_google_ads_keyword_planner_access requires blocked_reason.")
    if not isinstance(payload.get("required_google_ads_state"), list):
        errors.append(
            "configure_google_ads_keyword_planner_access requires required_google_ads_state."
        )
    if not isinstance(payload.get("helper_steps"), list):
        errors.append("configure_google_ads_keyword_planner_access requires helper_steps.")
    if not isinstance(payload.get("required_validation"), list):
        errors.append("configure_google_ads_keyword_planner_access requires required_validation.")
    if payload.get("apply_allowed") is not False:
        errors.append("configure_google_ads_keyword_planner_access must keep apply_allowed=false.")
    if payload.get("destructive") is not False:
        errors.append("configure_google_ads_keyword_planner_access must be non-destructive.")
    return errors
