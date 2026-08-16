from wilq.content.quality.section_heading_index import build_section_heading_index


def test_index_resolves_unique_heading_to_section_id() -> None:
    index = build_section_heading_index(
        [("section_01", "Zakres"), ("section_02", "Terminy")]
    )

    assert index.resolve("Zakres") == "section_01"
    assert not index.colliding("Zakres")


def test_index_returns_none_for_unknown_heading() -> None:
    index = build_section_heading_index([("section_01", "Zakres")])

    assert index.resolve("Nieznany") is None
    assert not index.colliding("Nieznany")


def test_index_returns_none_for_colliding_heading() -> None:
    index = build_section_heading_index(
        [("section_01", "Zakres"), ("section_02", "Zakres")]
    )

    assert index.resolve("Zakres") is None
    assert index.colliding("Zakres")
