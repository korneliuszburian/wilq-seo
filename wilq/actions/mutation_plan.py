from __future__ import annotations

from wilq.schemas import ActionMutationReadinessResponse, ActionRisk


def first_write_candidate(
    items: list[ActionMutationReadinessResponse],
) -> ActionMutationReadinessResponse | None:
    if not items:
        return None
    for item in items:
        if item.action_id == "act_apply_wordpress_draft_handoff":
            return item
    for item in items:
        if item.action_id == "act_prepare_wordpress_draft_handoff":
            return item
    candidates = [
        item
        for item in items
        if item.risk in {ActionRisk.low, ActionRisk.medium}
        and item.connector.startswith("wordpress")
    ]
    if candidates:
        return candidates[0]
    low_risk = [item for item in items if item.risk in {ActionRisk.low, ActionRisk.medium}]
    return low_risk[0] if low_risk else items[0]


def first_write_candidate_reason(
    item: ActionMutationReadinessResponse | None,
) -> str:
    if item is None:
        return "Brak akcji, którą można ocenić jako pierwszą propozycję zapisu."
    if item.action_id in {
        "act_apply_wordpress_draft_handoff",
        "act_prepare_wordpress_draft_handoff",
    }:
        blocker_codes = {blocker.code for blocker in item.blockers}
        if item.mutation_adapter is not None:
            if "missing_wordpress_draft_package_ready" not in blocker_codes:
                return (
                    "Pierwsza propozycja aktywowania zapisu to WordPress draft-only: "
                    "adapter boundary i paczka szkicu już istnieją, ale szkic nadal "
                    "wymaga handoffu, human review, preview/confirm/audit i jawnie "
                    "włączonego env live write. Publikacja i destrukcyjne zmiany są "
                    "zablokowane."
                )
            return (
                "Pierwsza propozycja aktywowania zapisu to WordPress draft-only: "
                "adapter boundary już istnieje, ale szkic nadal wymaga handoffu, "
                "paczki treści, preview/review/confirm/audit i jawnie włączonego "
                "env live write. Publikacja i destrukcyjne zmiany są zablokowane."
            )
        return (
            "Pierwsza propozycja aktywowania zapisu to WordPress draft-only: "
            "najpierw tworzy szkic, nie publikuje, ma osobny readiness endpoint i "
            "wymaga osobnego adaptera wykonania, env i pełnego audit trail."
        )
    return (
        "To najbliższa niskiego/średniego ryzyka akcja do oceny jako przyszły "
        "write adapter; nadal musi przejść readiness, preview, review i confirm."
    )


def activation_plan_steps(
    item: ActionMutationReadinessResponse | None,
) -> list[str]:
    if item is None:
        return ["Najpierw utwórz bezpieczną propozycję zapisu z dowodami."]
    steps = [
        "Utrzymaj zakres draft-only i brak publikacji/destrukcyjnych zmian.",
    ]
    if item.action_id == "act_apply_wordpress_draft_handoff":
        steps.append("Doprowadź apply-mode ActionObject przez validate, preview, review i confirm.")
    else:
        steps.append("Zbuduj osobny apply-capable ActionObject dla tej klasy zapisu.")
    blocker_codes = {blocker.code for blocker in item.blockers}
    if item.mutation_adapter is not None:
        if "missing_wordpress_draft_package_ready" in blocker_codes:
            steps.append(
                "Nie dodawaj kolejnego adaptera: boundary istnieje, a live write "
                "blokują handoff, paczka szkicu, audyt i env."
            )
        else:
            steps.append(
                "Nie dodawaj kolejnego adaptera: boundary i paczka szkicu istnieją, "
                "a live write blokują handoff, review/confirm/audit i env."
            )
    if "missing_payload_apply_allowed" in blocker_codes:
        steps.append("Odblokuj payload apply dopiero po przejściu review i readiness.")
    if "missing_preview_audit" in blocker_codes:
        steps.append("Wygeneruj i zapisz preview zmian przed jakimkolwiek write.")
    if "missing_confirmation_audit" in blocker_codes:
        steps.append("Zapisz review człowieka i jawne potwierdzenie operatora.")
    if "missing_impact_check" in blocker_codes:
        steps.append("Zapisz impact/readiness sanity check dla planowanej zmiany.")
    if "missing_mutation_adapter" in blocker_codes:
        steps.append("Dopiero potem dodaj adapter wykonania z redacted result i audit.")
    if "missing_wordpress_draft_handoff_ready" in blocker_codes:
        steps.append("Przygotuj zatwierdzony WordPress handoff dla wybranego work itemu.")
    if "missing_wordpress_draft_package_ready" in blocker_codes:
        steps.append(
            "Podepnij zatwierdzoną paczkę szkicu przed próbą podglądu wykonania."
        )
    if "missing_wordpress_draft_target_content_ready" in blocker_codes:
        steps.append(
            "Doprowadź konkretny target przez Claim Ledger, gotowość szkicu i "
            "human review zanim będzie można tworzyć draft."
        )
    if item.vendor_write_possible:
        steps.append("Przed live write wykonaj apply wyłącznie przez ActionObject i audit.")
    return steps


def activation_next_step(
    item: ActionMutationReadinessResponse | None,
) -> str:
    if item is None:
        return "Brak propozycji zapisu; najpierw wybierz niskiego ryzyka klasę draft-only."
    if item.action_id == "act_apply_wordpress_draft_handoff":
        if item.mutation_adapter is not None:
            blocker_codes = {blocker.code for blocker in item.blockers}
            if "missing_wordpress_draft_package_ready" not in blocker_codes:
                return (
                    "Najbliższy krok: zapisz human review i audit dla gotowej "
                    "paczki szkicu WordPress draft-only, potem przejdź preview/"
                    "confirm/audit ActionObject. Adapter boundary już istnieje; "
                    "live env/write zostaje wyłączony do jawnej decyzji."
                )
            return (
                "Najbliższy krok: przygotuj zatwierdzony handoff i paczkę szkicu "
                "dla WordPress draft-only, potem przejdź preview/review/confirm/"
                "audit. Adapter boundary już istnieje; live env/write zostaje "
                "wyłączony do jawnej decyzji."
            )
        return (
            "Najbliższy krok: doprowadź apply-mode WordPress draft-only do "
            "pełnego preview/review/confirm/audit i dodaj adapter boundary, ale "
            "env live write zostaje wyłączony do jawnej decyzji."
        )
    if item.action_id == "act_prepare_wordpress_draft_handoff":
        return (
            "Najbliższy krok: przygotuj osobny apply-capable ActionObject dla "
            "WordPress draft-only, ale zostaw env write wyłączony i publikację "
            "zablokowaną do czasu pełnego preview/review/confirm/audit."
        )
    return (
        "Najbliższy krok: doprecyzuj kontrakt apply dla tej akcji i utrzymaj "
        "write zablokowany do czasu pełnego readiness."
    )


def mutation_readiness_summary_next_step(
    items: list[ActionMutationReadinessResponse],
    blocker_counts: dict[str, int],
    first_write_candidate: ActionMutationReadinessResponse | None,
) -> str:
    if not items:
        return "Brakuje ActionObjectów do oceny gotowości zapisu."
    if any(item.would_attempt_vendor_write for item in items):
        return (
            "Co najmniej jedna akcja spełnia warunki zapisu; przed apply nadal "
            "wymagane jest jawne potwierdzenie operatora."
        )
    if first_write_candidate is not None and first_write_candidate.action_id == (
        "act_apply_wordpress_draft_handoff"
    ):
        first_blockers = {blocker.code for blocker in first_write_candidate.blockers}
        if {
            "missing_wordpress_draft_handoff_ready",
            "missing_wordpress_draft_package_ready",
        } & first_blockers:
            target = (
                f" dla: {first_write_candidate.target_label}"
                if first_write_candidate.target_label
                else ""
            )
            if "missing_wordpress_draft_package_ready" not in first_blockers:
                return (
                    "Pierwsza propozycja zapisu ma adapter boundary i paczkę szkicu, "
                    f"ale brakuje zatwierdzonego handoffu{target}. Najpierw zapisz "
                    "human review i audit przekazania do WordPress; live write nadal "
                    "zostaje wyłączony."
                )
            return (
                "Pierwsza propozycja zapisu ma adapter boundary, ale brakuje "
                f"zatwierdzonego handoffu i paczki szkicu{target}. Najpierw przejdź "
                "wybrany content item przez draft package, human review i "
                "WordPress handoff; live write nadal zostaje wyłączony."
            )
    if blocker_counts.get("missing_mutation_adapter"):
        return (
            "Najpierw wybierz jedną klasę zapisu i dodaj bezpieczny adapter "
            "podglądu/live; obecnie żaden vendor write nie powinien zostać wykonany."
        )
    if blocker_counts.get("missing_apply_mode"):
        return "Najpierw dodaj apply-capable ActionObject dla wybranej klasy zmian."
    return "Usuń pokazane blokery readiness przed próbą realnego zapisu."
