from pathlib import Path

from scripts.validate_source_registry import validate

REGISTRY = Path("docs/research/source-registry.md")


def test_source_registry_passes_current_contract() -> None:
    assert validate(REGISTRY) == []


def test_defer_without_its_own_recheck_fails_closed(tmp_path: Path) -> None:
    source = REGISTRY.read_text(encoding="utf-8")
    source = source.replace(
        (
            "WILQ-PLAIN-PL | S5 deterministic quality gate; właściciel WILQ Content Ops; "
            "re-check po walidowanym eksperymencie"
        ),
        "WILQ-PLAIN-PL | S5 deterministic quality gate; właściciel WILQ Content Ops",
        1,
    )
    candidate = tmp_path / "source-registry.md"
    candidate.write_text(source, encoding="utf-8")

    errors = validate(candidate)

    assert any("WILQ-PLAIN-PL: defer requires owner and re-check" in error for error in errors)


def test_malformed_source_row_returns_structured_error(tmp_path: Path) -> None:
    source = REGISTRY.read_text(encoding="utf-8")
    source = source.replace(
        next(line for line in source.splitlines() if line.startswith("| SEO-G2 |")),
        "| SEO-G2 | malformed | row |",
        1,
    )
    candidate = tmp_path / "source-registry.md"
    candidate.write_text(source, encoding="utf-8")

    errors = validate(candidate)

    assert any("source row must have 4 cells" in error for error in errors)


def test_defer_without_named_owner_fails_closed(tmp_path: Path) -> None:
    source = REGISTRY.read_text(encoding="utf-8")
    source = source.replace(
        "SEO-G3-D | owner: WILQ Content Ops; przyszły product contract, nie bieżący gate",
        "SEO-G3-D | brak named owner; przyszły product contract, nie bieżący gate",
        1,
    )
    candidate = tmp_path / "source-registry.md"
    candidate.write_text(source, encoding="utf-8")

    errors = validate(candidate)

    assert any("SEO-G3-D: defer requires owner and re-check" in error for error in errors)


def test_polish_recheck_wording_is_accepted(tmp_path: Path) -> None:
    source = REGISTRY.read_text(encoding="utf-8")
    source = source.replace(
        "re-check po walidowanym eksperymencie",
        "warunek ponownego sprawdzenia po walidowanym eksperymencie",
        1,
    )
    candidate = tmp_path / "source-registry.md"
    candidate.write_text(source, encoding="utf-8")

    assert validate(candidate) == []
