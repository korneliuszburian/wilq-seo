from __future__ import annotations

from typing import Any

from wilq.actions.validation_copy import missing, no_destructive_change, no_write, wrong
from wilq.schemas import ActionMode, ActionObject, ActionRisk, ActionStatus, OpportunityDomain

KEYWORD_PLANNER_ACCESS_ACTION_ID = "act_configure_google_ads_keyword_planner_access"
KEYWORD_PLANNER_ACCESS_ACTION_TYPE = "configure_google_ads_keyword_planner_access"
KEYWORD_PLANNER_ACCESS_BLOCKED_CLAIMS = [
    "rozmiar odbiorców",
    "prognoza",
    "wzrost konwersji",
    "zwrot z reklam",
    "zapis kierowania reklam",
    "skuteczność kampanii",
]


def keyword_planner_access_action(*, blocker: str, evidence_ids: list[str]) -> ActionObject:
    return ActionObject(
        id=KEYWORD_PLANNER_ACCESS_ACTION_ID,
        title="Odblokuj Keyword Planner dla Google Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=evidence_ids,
        human_diagnosis=(
            "Google Ads live read działa, ale wzbogacenie Keyword Planner jest "
            f"zablokowane przez Google Ads API: {blocker}. WILQ może używać "
            "oceny haseł źródłowych, ale nie może twierdzić nic o prognozie ani "
            "rozmiarze odbiorców."
        ),
        recommended_reason=(
            "Dopóki token deweloperski nie ma zatwierdzonego dostępu Keyword Planner, "
            "segmenty zostają bez prognozy i wzbogacenia. To jest zewnętrzna "
            "blokada dostępu, nie brak promptu."
        ),
        payload=keyword_planner_access_payload(blocker),
        validation_status="not_validated",
        created_by="system_keyword_planner_access_seed",
    )


def keyword_planner_access_payload(blocker: str) -> dict[str, Any]:
    return {
        "action_type": KEYWORD_PLANNER_ACCESS_ACTION_TYPE,
        "connector": "google_ads",
        "mode": "prepare_only",
        "blocked_api": "Keyword Planner",
        "blocked_reason": blocker,
        "required_google_ads_state": [
            "developer_access_approved_for_keyword_planner",
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
            "confirm_developer_access_approval",
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
    subject = "Dostęp do Keyword Plannera"
    if payload.get("connector") != "google_ads":
        errors.append(wrong(subject, "dotyczy tylko Google Ads"))
    if payload.get("mode") != "prepare_only":
        errors.append(wrong(subject, "musi pozostać etapem przygotowania"))
    if payload.get("blocked_api") != "Keyword Planner":
        errors.append(missing(subject, "informacji o blokowanym API"))
    if not isinstance(payload.get("blocked_reason"), str) or not payload["blocked_reason"].strip():
        errors.append(missing(subject, "powodu blokady"))
    if not isinstance(payload.get("required_google_ads_state"), list):
        errors.append(missing(subject, "wymaganego stanu Google Ads"))
    if not isinstance(payload.get("helper_steps"), list):
        errors.append(missing(subject, "kroków naprawy"))
    if not isinstance(payload.get("required_validation"), list):
        errors.append(missing(subject, "listy wymaganych sprawdzeń"))
    if payload.get("apply_allowed") is not False:
        errors.append(no_write(subject))
    if payload.get("destructive") is not False:
        errors.append(no_destructive_change(subject))
    return errors
