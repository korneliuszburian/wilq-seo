from __future__ import annotations

from wilq.schemas import ActionMutationReadinessBlocker, ActionMutationReadinessRequirement

MUTATION_READINESS_BLOCKER_COPY: dict[str, tuple[str, str, str]] = {
    "valid_action": (
        "Akcja nie jest jeszcze poprawnie sprawdzona",
        "Przed zapisem trzeba uruchomić walidację ActionObject i usunąć błędy.",
        "Uruchom validate dla tej akcji i wróć do readiness.",
    ),
    "apply_mode": (
        "Akcja jest tylko prepare/review",
        "Ta akcja nie ma kontraktu zapisu do zewnętrznego systemu.",
        "Użyj jej do review albo dodaj osobny apply-capable ActionObject.",
    ),
    "payload_apply_allowed": (
        "Payload nadal blokuje apply",
        "Zakres akcji nie pozwala jeszcze na próbę zapisu.",
        "Najpierw przygotuj bezpieczny payload apply po preview, review i confirm.",
    ),
    "evidence_present": (
        "Brakuje dowodów źródłowych",
        "WILQ nie zapisuje zmian bez identyfikatorów dowodów.",
        "Podepnij dowody źródłowe do akcji przed rozważeniem zapisu.",
    ),
    "connector_configured": (
        "Connector nie jest skonfigurowany",
        "Nie ma bezpiecznej ścieżki do vendor API bez działającego connectora.",
        "Napraw credentials/status connectora i odśwież readiness.",
    ),
    "preview_audit": (
        "Brakuje podglądu zmian",
        "Operator musi zobaczyć preview zanim WILQ dopuści zapis.",
        "Uruchom preview dla tej akcji.",
    ),
    "confirmation_audit": (
        "Brakuje potwierdzenia operatora",
        "WILQ wymaga jawnego confirm przed zapisem.",
        "Zapisz confirm po review i preview.",
    ),
    "impact_check": (
        "Brakuje sprawdzenia efektu",
        "Przed zapisem WILQ wymaga sanity checku wpływu/okna efektu.",
        "Uruchom impact-check lub dodaj odpowiedni kontrakt wpływu.",
    ),
    "risk_allowed": (
        "Ryzyko zapisu jest zbyt wysokie",
        "High/critical writes nie mają jeszcze obsługiwanej ścieżki bezpieczeństwa.",
        "Rozbij akcję na niższe ryzyko albo dodaj osobny model akceptacji.",
    ),
    "non_destructive": (
        "Akcja jest destrukcyjna",
        "Destrukcyjne zmiany są zablokowane do czasu osobnego kontraktu.",
        "Przygotuj niedestrukcyjną alternatywę albo nowy guard dla tej klasy zmian.",
    ),
    "mutation_adapter": (
        "Brakuje adaptera zapisu",
        "WILQ nie ma jeszcze implementacji vendor write dla tej akcji.",
        "Najpierw dodaj read-only preview i bezpieczny adapter podglądu/live dla connectora.",
    ),
    "wordpress_draft_write_readiness": (
        "WordPress draft write readiness blokuje zapis",
        "Osobny kontrakt WordPress draft write readiness nie pozwala jeszcze na live write.",
        "Sprawdź env, REST adapter i audyty w readiness szkicu WordPress.",
    ),
    "wordpress_draft_handoff_ready": (
        "Brakuje zatwierdzonego przekazania do WordPress",
        "Adapter draft-only nie ma jeszcze zatwierdzonego handoffu, który wolno zamienić na szkic.",
        "Doprowadź wybrany work item przez draft package, human review i WordPress handoff.",
    ),
    "wordpress_draft_package_ready": (
        "Brakuje paczki szkicu WordPress",
        (
            "Adapter nie może tworzyć wpisu z samego ActionObject; potrzebuje "
            "zatwierdzonej paczki treści."
        ),
        (
            "Przygotuj draft package z claim ledgerem, sekcjami i dowodami, "
            "potem wróć do handoffu."
        ),
    ),
    "wordpress_draft_target_content_ready": (
        "Target treści nie przeszedł jeszcze gotowości szkicu",
        (
            "Wybrany URL ma tylko zablokowany podgląd handoffu. Przed draft-only "
            "write musi przejść Claim Ledger, kontrolę wiedzy/twierdzeń, gotowość "
            "szkicu i review człowieka."
        ),
        (
            "Doprowadź ten content item przez Claim Ledger, draft package i human "
            "review; dopiero potem wróć do WordPress handoffu."
        ),
    ),
    "wordpress_draft_live_write_env": (
        "Env nie pozwala na zapis szkicu WordPress",
        "WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES nie jest jawnie włączone.",
        "Zostaw write wyłączony albo włącz env dopiero po pełnym preview/review/confirm.",
    ),
    "wordpress_rest_adapter_configured": (
        "REST adapter WordPress nie jest gotowy",
        "Connector WordPress nie ma pełnej konfiguracji REST do utworzenia szkicu.",
        "Uzupełnij konfigurację WordPress REST i sprawdź authoring profile.",
    ),
    "wordpress_write_authorization": (
        "Brakuje autoryzacji write z audytu",
        "WILQ nie zbudował jeszcze write_authorization z preview, review i confirm.",
        "Przejdź validate, preview, human review i confirm w ActionObject.",
    ),
}


def mutation_readiness_blockers(
    requirements: list[ActionMutationReadinessRequirement],
) -> list[ActionMutationReadinessBlocker]:
    blockers: list[ActionMutationReadinessBlocker] = []
    for requirement in requirements:
        if requirement.satisfied:
            continue
        label, reason, next_step = MUTATION_READINESS_BLOCKER_COPY.get(
            requirement.code,
            (
                f"Niespełniony warunek: {requirement.label}",
                "Ten warunek blokuje bezpieczny zapis zmian.",
                "Uzupełnij warunek i sprawdź readiness ponownie.",
            ),
        )
        blockers.append(
            ActionMutationReadinessBlocker(
                code=f"missing_{requirement.code}",
                label=label,
                reason=reason,
                next_step=next_step,
            )
        )
    return blockers
