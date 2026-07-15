from __future__ import annotations


def revision_conflict_next_step(code: str) -> str:
    if code == "apply_in_progress":
        return (
            "Trwa zapis dokładnie zatwierdzonej wersji do WordPress. Poczekaj na wynik "
            "tej próby, odśwież snapshot i dopiero potem zapisz lub oceń nową wersję."
        )
    if code == "stale_base":
        return (
            "Na serwerze jest nowsza wersja. Zachowaj swój tekst, porównaj zmiany "
            "i dopiero potem zapisz kolejną wersję na aktualnej bazie."
        )
    if code == "stale_revision":
        return (
            "Ta wersja nie jest już najnowsza. Odśwież snapshot i sprawdź aktualną "
            "wersję bez przenoszenia starej decyzji."
        )
    if code == "stale_review":
        return (
            "Ktoś zapisał decyzję dla tej wersji wcześniej. Odśwież snapshot, "
            "przeczytaj aktualną decyzję i dopiero potem zdecyduj ponownie."
        )
    if code == "digest_mismatch":
        return (
            "Identyfikator treści nie pasuje do zapisanej wersji. Odśwież snapshot "
            "i sprawdź dokładny tekst przed decyzją."
        )
    return "Odśwież snapshot zadania i wybierz istniejącą zapisaną wersję."


__all__ = ["revision_conflict_next_step"]
