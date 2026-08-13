import pytest

import wilq.content.knowledge.text_matching as text_matching


def test_normalized_term_matches_single_significant_token_fallback() -> None:
    assert text_matching.normalized_term_matches(
        "akredytowane pomiary",
        "Jak zaplanować pomiary i działania remediacyjne",
    )


def test_normalized_term_matches_rejects_unrelated_significant_tokens() -> None:
    assert not text_matching.normalized_term_matches(
        "sprawozdania odpadowe",
        "Jak zaplanować pomiary",
    )


def test_normalized_term_matches_fallback_ignores_short_tokens() -> None:
    assert not text_matching.normalized_term_matches(
        "plan sprawozdania",
        "Jak przygotować plan pomiarów",
    )


def test_normalized_term_matches_can_disable_relaxed_fallback() -> None:
    assert not text_matching.strict_normalized_term_matches(
        "akredytowane pomiary",
        "Jak zaplanować pomiary i działania remediacyjne",
    )


def test_normalized_term_matches_exact_phrase_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_on_token_matching(_term_token: str, _search_token: str) -> bool:
        raise AssertionError("exact phrase must return before token matching")

    monkeypatch.setattr(text_matching, "_token_matches", fail_on_token_matching)

    assert text_matching.normalized_term_matches(
        "akredytowane pomiary",
        "Zakres obejmuje akredytowane pomiary środowiskowe",
    )
