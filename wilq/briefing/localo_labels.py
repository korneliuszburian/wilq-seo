from __future__ import annotations


LOCALO_CONTRACT_LABELS = {
    "competitor_visibility": "widoczność konkurencji",
    "gbp_visibility": "widoczność profilu firmy w Google",
    "local_rankings": "rankingi lokalne",
    "local_tasks": "zadania lokalne",
    "mcp_initialize": "test dostępu",
    "place_inventory": "lista lokalizacji",
    "reviews": "opinie",
}

LOCALO_EVIDENCE_LABELS = {
    "access_token_presence": "potwierdzenie lokalnego dostępu",
    "mcp_initialize": "potwierdzenie dostępu Localo",
    "oauth_metadata": "potwierdzenie autoryzacji",
}

LOCALO_METRIC_FACT_LABELS = {
    "localo_active_place_count": "aktywne lokalizacje",
    "localo_avg_latest_grid_position": "średnia pozycja w siatce",
    "localo_avg_rating": "średnia ocena",
    "localo_avg_visibility_change": "zmiana widoczności",
    "localo_avg_visibility_current": "średnia widoczność",
    "localo_competitor_change_count": "zmiany konkurencji",
    "localo_competitor_count": "konkurenci",
    "localo_favorite_competitor_count": "obserwowani konkurenci",
    "localo_gbp_actions_total": "akcje profilu firmy w Google",
    "localo_gbp_impressions_total": "wyświetlenia profilu firmy w Google",
    "localo_gbp_metric_point_count": "punkty danych profilu firmy w Google",
    "localo_keyword_volume_count": "frazy z wolumenem",
    "localo_latest_grid_position_count": "pozycje z siatki",
    "localo_place_detail_count": "szczegóły lokalizacji",
    "localo_read_contract_count": "odczytane obszary",
    "localo_review_reply_rate": "udział odpowiedzi na opinie",
    "localo_reviews_count": "opinie",
    "localo_reviews_removed_count": "usunięte opinie",
    "localo_reviews_replied_count": "opinie z odpowiedzią",
    "localo_snapshot_reviews_count": "opinie w zrzucie",
    "localo_total_keyword_volume": "łączny wolumen fraz",
    "localo_tracked_keyword_count": "monitorowane frazy",
    "localo_visibility_score_count": "punkty widoczności",
}


def localo_contract_label(value: str) -> str:
    return LOCALO_CONTRACT_LABELS.get(value, "zakres danych Localo do sprawdzenia")


def localo_evidence_label(value: str) -> str:
    return LOCALO_EVIDENCE_LABELS.get(value, localo_contract_label(value))


def localo_metric_fact_label(value: str) -> str:
    return LOCALO_METRIC_FACT_LABELS.get(value, "metryka Localo do sprawdzenia")
