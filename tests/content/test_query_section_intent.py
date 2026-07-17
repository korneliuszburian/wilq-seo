from wilq.content.workflow.query_section_intent import assign_query_to_sections


def test_intent_assignment_separates_definition_applicability_and_obligations() -> None:
    sections = [
        ("Co to jest system", "Wyjaśnij definicję."),
        ("Dla kogo jest system", "Wyjaśnij, kogo dotyczy."),
        ("Obowiązki systemu dla firmy", "Wyjaśnij wymagania i przepisy."),
    ]

    assert assign_query_to_sections("system co to znaczy", sections) == [
        "Co to jest system"
    ]
    assert assign_query_to_sections("system dla kogo", sections) == [
        "Dla kogo jest system"
    ]
    assert assign_query_to_sections("obowiązki systemu", sections) == [
        "Obowiązki systemu dla firmy"
    ]
    assert assign_query_to_sections("system", sections) == []
    assert assign_query_to_sections("nieznany synonim systemu", sections) == []


def test_intent_assignment_keeps_service_and_locality_distinct() -> None:
    sections = [
        ("Doradztwo w ochronie środowiska", "Zakres usług dla firm."),
        ("Doradztwo środowiskowe Śląsk", "Lokalne wsparcie na Śląsku."),
    ]

    assert assign_query_to_sections("konsulting środowiskowy", sections) == []
    assert assign_query_to_sections("doradztwo środowiskowe śląsk", sections) == [
        "Doradztwo środowiskowe Śląsk"
    ]
    assert assign_query_to_sections("doradztwo środowiskowe kraków", sections) == []
    assert assign_query_to_sections("outsourcing środowiskowy ruda śląska", sections) == []
    assert assign_query_to_sections("doradztwo podatkowe", sections) == []
    assert assign_query_to_sections("outsourcing IT", sections) == []
    assert assign_query_to_sections("doradztwo środowiskowe opole", sections) == []
    assert assign_query_to_sections("doradztwo środowiskowe toruń", sections) == []
    assert assign_query_to_sections("doradztwo środowiskowe pomorskie", sections) == []
