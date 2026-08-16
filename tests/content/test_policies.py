import pytest

from wilq.content.workflow import policies


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", " TRUE "])
def test_wordpress_draft_writes_policy_accepts_only_supported_truthy_values(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setattr(policies, "variable_value", lambda name: value)

    assert policies.wordpress_draft_writes_enabled() is True


@pytest.mark.parametrize("value", [None, "", "0", "false", "no", "enabled"])
def test_wordpress_draft_writes_policy_fails_closed_for_other_values(
    monkeypatch: pytest.MonkeyPatch,
    value: str | None,
) -> None:
    monkeypatch.setattr(policies, "variable_value", lambda name: value)

    assert policies.wordpress_draft_writes_enabled() is False


def test_wordpress_dev_host_policy_requires_the_owned_dev_host() -> None:
    assert policies.wordpress_dev_host_allowed(None) is False
    assert policies.wordpress_dev_host_allowed("") is False
    assert policies.wordpress_dev_host_allowed("https://www.ekologus.pl/") is False
    assert policies.wordpress_dev_host_allowed("https://EKOLOGUS.DEV.PROUDSITE.PL/") is True
