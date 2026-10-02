from types import SimpleNamespace

from tests.content.test_full_draft_generation_v3 import _authorize, _case, _prepare
from wilq.content.drafts.full_draft_generation_v3_dispatch import dispatch_full_draft_generation_v3


def test_claim_without_worker_can_recover_same_run_once(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch)
    action = _prepare(case)
    _authorize(case, action)
    submissions = []

    def rejected(fn, *args):
        submissions.append("rejected")
        raise RuntimeError("synthetic-before-enqueue")

    def accepted(fn, *args):
        submissions.append("accepted")
        fn(*args)

    kwargs = dict(
        workflow_store=case.workflow_store,
        run_store=case.audit_store,
        snapshot_loader=lambda _: case.snapshot,
        client_factory=lambda: case.client,
    )
    first = dispatch_full_draft_generation_v3(
        action, executor=SimpleNamespace(submit=rejected), **kwargs
    )
    assert first.status == "blocked"
    claim = case.workflow_store.load_full_draft_generation_v3_dispatch(action)
    assert claim is not None and not case.turns
    dispatch_full_draft_generation_v3(action, executor=SimpleNamespace(submit=accepted), **kwargs)
    assert submissions == ["rejected", "accepted"]
    assert case.workflow_store.load_full_draft_generation_v3_dispatch(action) == claim
    assert case.turns
