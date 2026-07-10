from __future__ import annotations

from wilq.actions.content_refresh import (
    _first_metric_or_missing,
    _metric_sum_or_missing,
    content_contract_label,
)
from wilq.briefing.ads_diagnostics import _ads_status_label
from wilq.briefing.ahrefs_diagnostics import _ahrefs_status_label
from wilq.briefing.command_center import _decision_state_label
from wilq.briefing.localo_diagnostics import (
    _localo_bool_label,
    _localo_read_contract_status_label,
    _localo_section_status_label,
    _localo_token_presence_label,
)
from wilq.briefing.merchant_diagnostics import _merchant_status_label


def test_missing_domain_statuses_explain_unconfirmed_data_scope() -> None:
    assert _decision_state_label("missing") == "dane niepotwierdzone"
    assert _ads_status_label("missing") == "zakres danych Ads niepotwierdzony"
    assert _ahrefs_status_label("missing") == "dane Ahrefs niepotwierdzone"
    assert _merchant_status_label("missing") == "zakres danych Merchant niepotwierdzony"


def test_content_action_missing_labels_explain_unconfirmed_source_data() -> None:
    assert content_contract_label("missing") == "zakres treści niepotwierdzony"
    assert _metric_sum_or_missing([], "clicks") == "metryka GSC niepotwierdzona"
    assert _first_metric_or_missing([], "ctr") == "metryka GSC niepotwierdzona"


def test_localo_missing_statuses_explain_unconfirmed_contracts() -> None:
    assert _localo_section_status_label("missing") == "zakres danych niepodłączony"
    assert _localo_read_contract_status_label("missing") == "zakres danych niepotwierdzony"
    assert _localo_bool_label(None) == "niepotwierdzone"
    assert _localo_token_presence_label(False) == "token nieobecny"
    assert _localo_token_presence_label(None) == "stan tokena niepotwierdzony"
