from __future__ import annotations

import unicodedata


def normalize_search_text(value: str) -> str:
    transliterated = value.casefold().replace("ł", "l")
    decomposed = unicodedata.normalize("NFKD", transliterated)
    return " ".join(
        "".join(
            character if character.isalnum() else " "
            for character in decomposed
            if not unicodedata.combining(character)
        ).split()
    )


def normalized_term_matches(term: str, normalized_search_text: str) -> bool:
    normalized_term = normalize_search_text(term)
    if not normalized_term:
        return False
    if f" {normalized_term} " in f" {normalized_search_text} ":
        return True
    term_tokens = normalized_term.split()
    search_tokens = normalized_search_text.split()
    if any(len(token) < 5 for token in term_tokens):
        return False
    return any(
        all(
            _token_matches(token, search_tokens[start + offset])
            for offset, token in enumerate(term_tokens)
        )
        for start in range(len(search_tokens) - len(term_tokens) + 1)
    )


def _token_matches(term_token: str, search_token: str) -> bool:
    common = 0
    for left, right in zip(term_token, search_token, strict=False):
        if left != right:
            break
        common += 1
    if common == len(term_token):
        return common >= 5
    return (
        term_token[-1] in "aeiouąęó"
        and common >= 5
        and common / min(len(term_token), len(search_token)) >= 0.75
    )
