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


def normalized_term_matches(
    term: str,
    normalized_search_text: str,
) -> bool:
    """Match exact phrase, then contiguous tokens, then one significant token.

    This precedence keeps the single-token check as a relaxed fallback only.
    """
    return _normalized_term_matches(term, normalized_search_text, relaxed=True)


def strict_normalized_term_matches(term: str, normalized_search_text: str) -> bool:
    """Match an exact phrase or contiguous significant-token sequence only."""
    return _normalized_term_matches(term, normalized_search_text, relaxed=False)


def _normalized_term_matches(
    term: str,
    normalized_search_text: str,
    *,
    relaxed: bool,
) -> bool:
    normalized_term = normalize_search_text(term)
    if not normalized_term:
        return False
    if f" {normalized_term} " in f" {normalized_search_text} ":
        return True
    term_tokens = normalized_term.split()
    search_tokens = normalized_search_text.split()
    if all(len(token) >= 5 for token in term_tokens) and any(
        all(
            _token_matches(token, search_tokens[start + offset])
            for offset, token in enumerate(term_tokens)
        )
        for start in range(len(search_tokens) - len(term_tokens) + 1)
    ):
        return True
    if not relaxed:
        return False
    return any(
        _token_matches(term_token, search_token)
        for term_token in term_tokens
        if len(term_token) >= 5
        for search_token in search_tokens
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
