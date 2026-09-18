from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from io import StringIO
from os import stat

import pytest

import scripts.trusted_local_confirmation as trusted_cli
from scripts.trusted_local_confirmation import issue_interactive_grant
from wilq.audit.trusted_local_confirmation import (
    TRUSTED_LOCAL_CONFIRMATION_PHRASE,
    TrustedLocalConfirmationAuthority,
    TrustedLocalConfirmationBlocked,
    TrustedLocalConfirmationError,
    TrustedLocalConfirmationStore,
)


def test_trusted_grant_requires_tty_and_exact_phrase(tmp_path) -> None:
    clock_time = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)
    authority = TrustedLocalConfirmationAuthority(
        store=TrustedLocalConfirmationStore(tmp_path / "grants.sqlite3"),
        signing_key=b"test-signing-key-which-is-long-enough",
        clock=lambda: clock_time,
        uid_reader=lambda: 1234,
        random_bytes=lambda size: b"n" * size,
    )
    kwargs = dict(
        principal_id="local_operator",
        workspace_id="ekologus_local_pilot",
        action_id="act_content_research_fact_promotion_example",
        payload_digest="a" * 64,
        snapshot_digest="b" * 64,
    )

    with pytest.raises(TrustedLocalConfirmationBlocked, match="TTY"):
        authority.issue(
            **kwargs,
            is_tty=False,
            confirmation_phrase=TRUSTED_LOCAL_CONFIRMATION_PHRASE,
        )
    with pytest.raises(TrustedLocalConfirmationBlocked, match="phrase"):
        authority.issue(**kwargs, is_tty=True, confirmation_phrase="wrong")

    token = authority.issue(
        **kwargs,
        is_tty=True,
        confirmation_phrase=TRUSTED_LOCAL_CONFIRMATION_PHRASE,
    )
    receipt = authority.consume(
        token,
        action_id=kwargs["action_id"],
        payload_digest=kwargs["payload_digest"],
        snapshot_digest=kwargs["snapshot_digest"],
        workspace_id=kwargs["workspace_id"],
    )

    assert receipt.principal_id == "local_operator"
    assert receipt.trust_level == "local_confirmed"
    assert receipt.os_uid == 1234
    assert authority.receipt_for(**kwargs) == receipt
    with pytest.raises(TrustedLocalConfirmationBlocked, match="replay"):
        authority.consume(
            token,
            action_id=kwargs["action_id"],
            payload_digest=kwargs["payload_digest"],
            snapshot_digest=kwargs["snapshot_digest"],
            workspace_id=kwargs["workspace_id"],
        )


def test_trusted_grant_binding_expiry_signature_and_uid_fail_closed(tmp_path) -> None:
    current = [datetime(2026, 9, 14, 12, 0, tzinfo=UTC)]
    uid = [1234]
    authority = TrustedLocalConfirmationAuthority(
        store=TrustedLocalConfirmationStore(tmp_path / "grants.sqlite3"),
        signing_key=b"test-signing-key-which-is-long-enough",
        clock=lambda: current[0],
        uid_reader=lambda: uid[0],
        random_bytes=lambda size: b"q" * size,
    )
    kwargs = dict(
        principal_id="local_operator",
        workspace_id="ekologus_local_pilot",
        action_id="act_content_research_fact_promotion_example",
        payload_digest="a" * 64,
        snapshot_digest="b" * 64,
    )
    token = authority.issue(
        **kwargs,
        is_tty=True,
        confirmation_phrase=TRUSTED_LOCAL_CONFIRMATION_PHRASE,
        ttl_seconds=5,
    )
    for field, value in (
        ("action_id", "wrong_action"),
        ("payload_digest", "c" * 64),
        ("snapshot_digest", "d" * 64),
        ("workspace_id", "wrong_workspace"),
    ):
        consume_kwargs = {
            "action_id": kwargs["action_id"],
            "payload_digest": kwargs["payload_digest"],
            "snapshot_digest": kwargs["snapshot_digest"],
            "workspace_id": kwargs["workspace_id"],
        }
        consume_kwargs[field] = value
        with pytest.raises(TrustedLocalConfirmationBlocked):
            authority.consume(token, **consume_kwargs)

    uid[0] = 9999
    with pytest.raises(TrustedLocalConfirmationBlocked, match="UID"):
        authority.consume(
            token,
            action_id=kwargs["action_id"],
            payload_digest=kwargs["payload_digest"],
            snapshot_digest=kwargs["snapshot_digest"],
            workspace_id=kwargs["workspace_id"],
        )
    uid[0] = 1234
    current[0] += timedelta(seconds=5)
    with pytest.raises(TrustedLocalConfirmationBlocked, match="expired"):
        authority.consume(
            token,
            action_id=kwargs["action_id"],
            payload_digest=kwargs["payload_digest"],
            snapshot_digest=kwargs["snapshot_digest"],
            workspace_id=kwargs["workspace_id"],
        )
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(TrustedLocalConfirmationBlocked, match="signature"):
        authority.consume(
            tampered,
            action_id=kwargs["action_id"],
            payload_digest=kwargs["payload_digest"],
            snapshot_digest=kwargs["snapshot_digest"],
            workspace_id=kwargs["workspace_id"],
        )


def test_runtime_key_is_private_and_store_does_not_contain_token(tmp_path) -> None:
    key_path = tmp_path / "trusted.key"
    store_path = tmp_path / "grants.sqlite3"
    authority = TrustedLocalConfirmationAuthority(
        store=TrustedLocalConfirmationStore(store_path),
        key_path=key_path,
        clock=lambda: datetime(2026, 9, 14, 12, 0, tzinfo=UTC),
        uid_reader=lambda: 1234,
    )
    token = authority.issue(
        principal_id="local_operator",
        workspace_id="ekologus_local_pilot",
        action_id="act_content_research_fact_promotion_example",
        payload_digest="a" * 64,
        snapshot_digest="b" * 64,
        is_tty=True,
        confirmation_phrase=TRUSTED_LOCAL_CONFIRMATION_PHRASE,
    )
    authority.consume(
        token,
        action_id="act_content_research_fact_promotion_example",
        payload_digest="a" * 64,
        snapshot_digest="b" * 64,
        workspace_id="ekologus_local_pilot",
    )
    assert stat(key_path).st_mode & 0o777 == 0o600
    assert stat(store_path).st_mode & 0o777 == 0o600
    assert token.encode() not in key_path.read_bytes()
    assert token.encode() not in store_path.read_bytes()


def test_cli_shows_exact_binding_before_phrase_and_rejects_non_tty(tmp_path) -> None:
    authority = TrustedLocalConfirmationAuthority(
        store=TrustedLocalConfirmationStore(tmp_path / "grants.sqlite3"),
        signing_key=b"test-signing-key-which-is-long-enough",
        clock=lambda: datetime(2026, 9, 14, 12, 0, tzinfo=UTC),
        uid_reader=lambda: 1234,
    )
    output = StringIO()
    token = issue_interactive_grant(
        authority=authority,
        action_id="act_content_research_fact_promotion_example",
        payload_digest="a" * 64,
        snapshot_digest="b" * 64,
        workspace_id="ekologus_local_pilot",
        stdin=StringIO(TRUSTED_LOCAL_CONFIRMATION_PHRASE + "\n"),
        stdout=output,
        is_tty=True,
    )
    rendered = output.getvalue()
    assert token in rendered
    assert "action ID: act_content_research_fact_promotion_example" in rendered
    assert f"action payload digest: {'a' * 64}" in rendered
    assert f"promotion snapshot digest: {'b' * 64}" in rendered
    assert "workspace: ekologus_local_pilot" in rendered
    assert "OS UID: 1234" in rendered
    with pytest.raises(TrustedLocalConfirmationBlocked, match="TTY"):
        issue_interactive_grant(
            authority=authority,
            action_id="act_content_research_fact_promotion_example",
            payload_digest="a" * 64,
            snapshot_digest="b" * 64,
            workspace_id="ekologus_local_pilot",
            stdin=StringIO(TRUSTED_LOCAL_CONFIRMATION_PHRASE + "\n"),
            stdout=StringIO(),
            is_tty=False,
        )


def test_consumed_receipt_expires_before_it_can_authorize_lifecycle(tmp_path) -> None:
    current = [datetime(2026, 9, 14, 12, 0, tzinfo=UTC)]
    authority = TrustedLocalConfirmationAuthority(
        store=TrustedLocalConfirmationStore(tmp_path / "grants.sqlite3"),
        signing_key=b"test-signing-key-which-is-long-enough",
        clock=lambda: current[0],
        uid_reader=lambda: 1234,
    )
    binding = {
        "principal_id": "local_operator",
        "workspace_id": "ekologus_local_pilot",
        "action_id": "act_content_research_fact_promotion_example",
        "payload_digest": "a" * 64,
        "snapshot_digest": "b" * 64,
    }
    token = authority.issue(
        **{key: value for key, value in binding.items() if key != "principal_id"},
        is_tty=True,
        confirmation_phrase=TRUSTED_LOCAL_CONFIRMATION_PHRASE,
        ttl_seconds=5,
        principal_id=binding["principal_id"],
    )
    receipt = authority.consume(
        token,
        action_id=binding["action_id"],
        payload_digest=binding["payload_digest"],
        snapshot_digest=binding["snapshot_digest"],
        workspace_id=binding["workspace_id"],
    )
    current[0] += timedelta(seconds=5)
    with pytest.raises(TrustedLocalConfirmationBlocked, match="expired"):
        authority.receipt_for(**binding)
    assert receipt.expires_at <= current[0]


def test_consumed_receipt_rechecks_current_uid_before_reuse(tmp_path) -> None:
    uid = [1234]
    authority = TrustedLocalConfirmationAuthority(
        store=TrustedLocalConfirmationStore(tmp_path / "grants.sqlite3"),
        signing_key=b"test-signing-key-which-is-long-enough",
        clock=lambda: datetime(2026, 9, 14, 12, 0, tzinfo=UTC),
        uid_reader=lambda: uid[0],
    )
    binding = {
        "principal_id": "local_operator",
        "workspace_id": "ekologus_local_pilot",
        "action_id": "act_content_research_fact_promotion_example",
        "payload_digest": "a" * 64,
        "snapshot_digest": "b" * 64,
    }
    token = authority.issue(
        **{key: value for key, value in binding.items() if key != "principal_id"},
        is_tty=True,
        confirmation_phrase=TRUSTED_LOCAL_CONFIRMATION_PHRASE,
        principal_id=binding["principal_id"],
    )
    authority.consume(
        token,
        action_id=binding["action_id"],
        payload_digest=binding["payload_digest"],
        snapshot_digest=binding["snapshot_digest"],
        workspace_id=binding["workspace_id"],
    )
    uid[0] = 9999
    with pytest.raises(TrustedLocalConfirmationBlocked, match="UID"):
        authority.receipt_for(**binding)


def test_cli_uid_failure_returns_safe_nonzero_without_traceback(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _TTYStringIO(StringIO):
        def isatty(self) -> bool:
            return True

    authority = TrustedLocalConfirmationAuthority(
        store=TrustedLocalConfirmationStore(tmp_path / "grants.sqlite3"),
        signing_key=b"test-signing-key-which-is-long-enough",
        uid_reader=lambda: (_ for _ in ()).throw(OSError("uid unavailable")),
    )
    monkeypatch.setattr(trusted_cli, "trusted_local_confirmation_authority", lambda: authority)
    stdin = _TTYStringIO(TRUSTED_LOCAL_CONFIRMATION_PHRASE + "\n")
    stdout = _TTYStringIO()
    stderr = _TTYStringIO()
    monkeypatch.setattr(trusted_cli.sys, "stdin", stdin)
    monkeypatch.setattr(trusted_cli.sys, "stdout", stdout)
    monkeypatch.setattr(trusted_cli.sys, "stderr", stderr)

    status = trusted_cli.main(
        [
            "issue",
            "--action-id",
            "act_content_research_fact_promotion_example",
            "--payload-digest",
            "a" * 64,
            "--snapshot-digest",
            "b" * 64,
        ]
    )

    assert status != 0
    assert "uid" in stderr.getvalue().lower()
    assert "traceback" not in stderr.getvalue().lower()


def test_uid_and_key_failures_are_typed_and_symlink_is_rejected(tmp_path) -> None:
    uid_failure = TrustedLocalConfirmationAuthority(
        store=TrustedLocalConfirmationStore(tmp_path / "uid.sqlite3"),
        signing_key=b"test-signing-key-which-is-long-enough",
        uid_reader=lambda: (_ for _ in ()).throw(OSError("uid unavailable")),
    )
    with pytest.raises(TrustedLocalConfirmationError):
        uid_failure.issue(
            principal_id="local_operator",
            workspace_id="ekologus_local_pilot",
            action_id="act_content_research_fact_promotion_example",
            payload_digest="a" * 64,
            snapshot_digest="b" * 64,
            is_tty=True,
            confirmation_phrase=TRUSTED_LOCAL_CONFIRMATION_PHRASE,
        )

    target = tmp_path / "real.key"
    target.write_bytes(b"k" * 32)
    symlink = tmp_path / "trusted.key"
    symlink.symlink_to(target)
    authority = TrustedLocalConfirmationAuthority(
        store=TrustedLocalConfirmationStore(tmp_path / "key.sqlite3"),
        key_path=symlink,
        clock=lambda: datetime(2026, 9, 14, 12, 0, tzinfo=UTC),
        uid_reader=lambda: 1234,
    )
    with pytest.raises(TrustedLocalConfirmationError, match="symlink"):
        authority.issue(
            principal_id="local_operator",
            workspace_id="ekologus_local_pilot",
            action_id="act_content_research_fact_promotion_example",
            payload_digest="a" * 64,
            snapshot_digest="b" * 64,
            is_tty=True,
            confirmation_phrase=TRUSTED_LOCAL_CONFIRMATION_PHRASE,
        )


def test_concurrent_consumers_allow_exactly_one_receipt(tmp_path) -> None:
    authority = TrustedLocalConfirmationAuthority(
        store=TrustedLocalConfirmationStore(tmp_path / "race.sqlite3"),
        signing_key=b"test-signing-key-which-is-long-enough",
        clock=lambda: datetime(2026, 9, 14, 12, 0, tzinfo=UTC),
        uid_reader=lambda: 1234,
    )
    token = authority.issue(
        principal_id="local_operator",
        workspace_id="ekologus_local_pilot",
        action_id="act_content_research_fact_promotion_example",
        payload_digest="a" * 64,
        snapshot_digest="b" * 64,
        is_tty=True,
        confirmation_phrase=TRUSTED_LOCAL_CONFIRMATION_PHRASE,
    )

    def consume() -> str:
        try:
            authority.consume(
                token,
                action_id="act_content_research_fact_promotion_example",
                payload_digest="a" * 64,
                snapshot_digest="b" * 64,
                workspace_id="ekologus_local_pilot",
            )
        except TrustedLocalConfirmationBlocked as error:
            return error.code
        return "created"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: consume(), range(2)))
    assert sorted(outcomes) == ["created", "trusted_local_confirmation_replay"]
