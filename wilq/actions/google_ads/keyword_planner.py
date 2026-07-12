from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wilq.actions.validation_copy import missing, no_destructive_change, no_write, wrong
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionPreviewCardViewModel,
    ActionPreviewRowViewModel,
    ActionRisk,
    ActionStatus,
    OpportunityDomain,
)

PreviewRow = Callable[[str, str], ActionPreviewRowViewModel]
StringList = Callable[[Any], list[str]]
StateLabel = Callable[[Any], str]

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


def keyword_planner_access_preview_cards(
    payload: dict[str, Any],
    *,
    preview_row: PreviewRow,
    string_list: StringList,
    apply_state_label: StateLabel,
) -> list[ActionPreviewCardViewModel]:
    """Render Keyword Planner access blocker without exposing technical payloads."""
    rows = [
        preview_row(
            "Zablokowany dostęp",
            str(payload.get("blocked_api") or "Keyword Planner"),
        ),
        preview_row(
            "Powód",
            "token deweloperski nie ma zatwierdzonego dostępu do Keyword Plannera",
        ),
    ]
    required_state_labels = string_list(payload.get("required_google_ads_state_labels"))
    if required_state_labels:
        rows.append(preview_row("Wymagany stan", ", ".join(required_state_labels[:4])))
    rows.append(
        preview_row(
            "Następny krok",
            "sprawdź status tokena deweloperskiego w Google Ads, "
            "a po akceptacji ponów odczyt danych",
        )
    )
    requirement_labels = string_list(payload.get("required_validation_labels"))
    if requirement_labels:
        rows.append(preview_row("Warunki sprawdzenia", ", ".join(requirement_labels[:4])))
    blocked_claim_labels = string_list(payload.get("blocked_claim_labels"))
    if blocked_claim_labels:
        rows.append(
            preview_row(
                "Czego nie wolno twierdzić",
                ", ".join(blocked_claim_labels[:4]),
            )
        )
    return [
        ActionPreviewCardViewModel(
            id="keyword_planner_access_preview",
            kind="google_ads_keyword_planner_access_review",
            title_label="Dostęp do Keyword Plannera do odblokowania",
            subtitle_label="blokada dostępu bez zapisu zmian",
            status_label="zapis zmian zablokowany",
            rows=rows,
            apply_state_label=apply_state_label(payload.get("apply_allowed")),
            system_readiness_label="wymaga zmiany po stronie Google Ads",
        )
    ]
