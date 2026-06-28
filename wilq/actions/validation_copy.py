from __future__ import annotations


def missing(subject: str, detail: str) -> str:
    return f"{subject}: brakuje {detail}."


def wrong(subject: str, detail: str) -> str:
    return f"{subject}: {detail}."


def row(subject: str, index: int) -> str:
    return f"{subject}, wiersz {index + 1}"


def no_write(subject: str) -> str:
    return f"{subject}: to musi pozostać etapem sprawdzenia, bez zapisu zmian."


def no_api_write(subject: str) -> str:
    return f"{subject}: nie może być oznaczone jako gotowe do zapisu zmian."


def no_destructive_change(subject: str) -> str:
    return f"{subject}: nie może być zmianą destrukcyjną."


def missing_evidence(subject: str) -> str:
    return missing(subject, "dowodów w WILQ")


def missing_review_check(subject: str) -> str:
    return missing(subject, "jednego z wymaganych sprawdzeń")
