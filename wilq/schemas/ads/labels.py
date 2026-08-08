from __future__ import annotations

__all__ = [
    "_operator_number_label",
    "_operator_micros_label",
    "_operator_percent_label",
    "_ads_campaign_display_label",
    "_ads_change_event_display_label",
    "_ads_change_resource_display_label",
    "_ads_ad_group_display_label",
    "_ads_read_contract_status_label",
]



def _operator_number_label(
    value: int | float | None,
    *,
    missing_label: str,
    max_fraction_digits: int = 2,
) -> str:
    if value is None:
        return missing_label
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    text = f"{value:,.{max_fraction_digits}f}".rstrip("0").rstrip(".")
    return text.replace(",", " ").replace(".", ",")


def _operator_micros_label(value: int | float | None, *, missing_label: str) -> str:
    if value is None:
        return missing_label
    return f"{_operator_number_label(value / 1_000_000, missing_label=missing_label)} jedn. konta"


def _operator_percent_label(value: int | float | None, *, missing_label: str) -> str:
    if value is None:
        return missing_label
    return f"{_operator_number_label(value * 100, missing_label=missing_label)}%"


def _ads_campaign_display_label(
    campaign_name: str | None,
    campaign_id: str | None,
) -> str:
    name = (campaign_name or "").strip()
    if name:
        return name
    if campaign_id:
        return "kampania do sprawdzenia w szczegółach technicznych"
    return "brak kampanii w odczycie"


def _ads_change_event_display_label(change_event_id: str | None) -> str:
    if change_event_id:
        return "zmiana do sprawdzenia w szczegółach technicznych"
    return "brak identyfikatora zmiany w odczycie"


def _ads_change_resource_display_label(
    resource_type_label: str | None,
    change_resource_id: str | None,
) -> str:
    resource = (resource_type_label or "").strip() or "zasób zmiany"
    if change_resource_id:
        return f"{resource} do sprawdzenia w szczegółach technicznych"
    return f"{resource} bez identyfikatora w odczycie"


def _ads_ad_group_display_label(
    ad_group_name: str | None,
    ad_group_id: str | None,
) -> str:
    name = (ad_group_name or "").strip()
    if name:
        return name
    if ad_group_id:
        return "grupa reklam do sprawdzenia w szczegółach technicznych"
    return "brak grupy reklam w odczycie"


def _ads_read_contract_status_label(status: str) -> str:
    labels = {
        "ready": "gotowe",
        "blocked": "zablokowane",
    }
    return labels.get(status, "status do sprawdzenia")
