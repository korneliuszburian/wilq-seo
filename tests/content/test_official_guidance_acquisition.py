from __future__ import annotations

import json
import socket
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from apps.api.wilq_api.routers import content_evidence_acquisition as acquisition_router
from tests.content.initial_draft_authority_fakes import exact_public_bdo_run
from tests.content.test_delivery_identity_binding import _command as identity_command
from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationProjection,
    ContentProductionClassificationRow,
)
from wilq.content.workflow.delivery_identity import (
    ContentDeliveryIdentityBinding,
    content_delivery_identity_digest,
    content_delivery_identity_logical_id,
)
from wilq.content.workflow.evidence_acquisition_contracts import (
    EvidenceAcquisitionStartCommand,
)
from wilq.content.workflow.evidence_acquisition_coordinator import (
    EvidenceAcquisitionCoordinator,
)
from wilq.content.workflow.official_guidance import (
    OFFICIAL_GUIDANCE_CANDIDATE_ID,
    OFFICIAL_GUIDANCE_CANONICAL_PATH,
    OFFICIAL_GUIDANCE_SOURCE_HOST,
    OFFICIAL_GUIDANCE_SOURCE_PATH,
    OFFICIAL_GUIDANCE_SOURCE_URL,
    OfficialGuidanceHTTPSReader,
    OfficialGuidanceObservationAdapter,
    OfficialGuidanceReadError,
    official_guidance_candidates,
)
from wilq.content.workflow.research_proposal import (
    EvidenceResearchCoordinator,
    ResearcherStructuredOutput,
    _output_blocker,
)
from wilq.content.workflow.store.store import ContentWorkflowStore


def test_iso_official_guidance_candidate_is_exactly_bound_to_target_path() -> None:
    candidates = official_guidance_candidates()
    candidate = next(
        item for item in candidates if item.candidate_id == OFFICIAL_GUIDANCE_CANDIDATE_ID
    )

    assert candidate.canonical_path == OFFICIAL_GUIDANCE_CANONICAL_PATH
    assert candidate.source_url == (
        "https://committee.iso.org/sites/tc309/home/projects/published/"
        "iso-37301-compliance-management.html"
    )
    assert candidate.allowed_claim_scope
    assert all(
        forbidden not in " ".join(candidate.allowed_claim_scope).casefold()
        for forbidden in ("certification guarantee", "environmental compliance guarantee")
    )


def test_official_selector_is_valid_only_for_official_primary() -> None:
    command = EvidenceAcquisitionStartCommand.model_validate(
        {
            "subject": {
                "subject_kind": "identity_binding",
                "identity_binding_id": "content_delivery_identity_00e1aa78372dcf3d38768973",
            },
            "research_question": "Jaki zakres ma ISO 37301?",
            "source_intent": "official_primary",
            "source_selector": {
                "selector_kind": "official_primary",
                "candidate_id": OFFICIAL_GUIDANCE_CANDIDATE_ID,
            },
        },
        strict=True,
    )

    assert command.source_selector is not None
    assert command.source_selector.candidate_id == OFFICIAL_GUIDANCE_CANDIDATE_ID


@pytest.mark.parametrize(
    ("proposed_claim", "scope", "blocked"),
    [
        (
            "ISO 37301 is a current international compliance management systems standard.",
            "ISO 37301 — compliance management systems",
            False,
        ),
        (
            "ISO 37301 is a current international compliance management systems standard.",
            "ISO 37301 guidance",
            True,
        ),
        (
            "ISO 37301 is a current international compliance management systems standard.",
            "ISO 37301 gwarantuje zgodność z prawem.",
            True,
        ),
        (
            "ISO 37301 gwarantuje zgodność z prawem.",
            "ISO 37301 — compliance management systems",
            True,
        ),
        (
            "Nonsense claim unrelated to the candidate.",
            "ISO 37301 — compliance management systems",
            True,
        ),
    ],
)
def test_official_guidance_claim_must_be_exact_allowed_candidate_string(
    proposed_claim: str, scope: str, blocked: bool
) -> None:
    candidate = official_guidance_candidates()[0]
    adapter = OfficialGuidanceObservationAdapter(
        material_reader=lambda url: SimpleNamespace(
            url=url,
            content_text="Independent excerpt about ISO 37301.",
            extraction_region="test.body",
        ),
        clock=lambda: datetime(2026, 9, 20, 12, 0, tzinfo=UTC),
    )
    observation = adapter.read(
        candidate_id=candidate.candidate_id,
        source_url=candidate.source_url,
        canonical_path=candidate.canonical_path,
    )
    output = ResearcherStructuredOutput(
        proposed_claim=proposed_claim,
        scope=scope,
        observation_ids=(observation.observation_id,),
        contradictions=(),
        unknowns=(),
    )

    blocker = _output_blocker(output, observation, candidate=candidate)

    assert (blocker is not None) is blocked
    if blocked:
        assert blocker is not None
        assert blocker.code == "official_guidance_scope_exceeded"


class _FakePinnedSocket:
    def __init__(self, response: bytes) -> None:
        self._response = response
        self.connected_to: tuple[object, ...] | None = None
        self.request: bytes | None = None
        self.timeout: float | None = None
        self.closed = False

    def settimeout(self, value: float) -> None:
        self.timeout = value

    def connect(self, address: tuple[object, ...]) -> None:
        self.connected_to = address

    def sendall(self, value: bytes) -> None:
        self.request = value

    def recv(self, size: int) -> bytes:
        if not self._response:
            return b""
        value, self._response = self._response[:size], self._response[size:]
        return value

    def close(self) -> None:
        self.closed = True


class _FailingConnectSocket(_FakePinnedSocket):
    def __init__(self, clock: _FakeClock) -> None:
        super().__init__(b"")
        self._clock = clock

    def connect(self, address: tuple[object, ...]) -> None:
        self._clock.value += 1.0
        raise OSError(101, f"network unreachable: {address}")


class _FakeTLSContext:
    def __init__(self) -> None:
        self.server_hostname: str | None = None

    def wrap_socket(self, raw_socket: _FakePinnedSocket, *, server_hostname: str):
        self.server_hostname = server_hostname
        return raw_socket


def _fake_reader(response: bytes):
    sockets: list[_FakePinnedSocket] = []
    contexts: list[_FakeTLSContext] = []

    def resolver(*_args: object, **_kwargs: object):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            )
        ]

    def socket_factory(*_args: object):
        item = _FakePinnedSocket(response)
        sockets.append(item)
        return item

    def context_factory():
        item = _FakeTLSContext()
        contexts.append(item)
        return item

    return (
        OfficialGuidanceHTTPSReader(
            resolver=resolver,
            socket_factory=socket_factory,
            tls_context_factory=context_factory,
        ),
        sockets,
        contexts,
    )


def test_pinned_reader_connects_to_validated_ip_and_extracts_visible_html() -> None:
    body = (
        b"<html><body><nav>ignore nav</nav><main>ISO 37301 guidance"
        b"<script>ignore script</script></main></body></html>"
    )
    response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/html; charset=UTF-8\r\n"
        + f"Content-Length: {len(body)}\r\n".encode()
        + b"\r\n"
        + body
    )
    reader, sockets, contexts = _fake_reader(response)

    material = reader.read(OFFICIAL_GUIDANCE_SOURCE_URL)

    assert material.url == OFFICIAL_GUIDANCE_SOURCE_URL
    assert material.content_text == "ISO 37301 guidance"
    assert sockets[0].connected_to == ("93.184.216.34", 443)
    assert contexts[0].server_hostname == OFFICIAL_GUIDANCE_SOURCE_HOST
    assert sockets[0].request is not None
    assert (
        f"GET {OFFICIAL_GUIDANCE_SOURCE_PATH} HTTP/1.1".encode()
        in sockets[0].request
    )
    assert f"Host: {OFFICIAL_GUIDANCE_SOURCE_HOST}\r\n".encode() in sockets[0].request
    assert b"Accept-Encoding: identity\r\n" in sockets[0].request


def test_pinned_reader_retries_next_validated_address_without_reresolving() -> None:
    body = b"<html><body>ipv4 success</body></html>"
    response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n"
        + f"Content-Length: {len(body)}\r\n\r\n".encode()
        + body
    )
    clock = _FakeClock()
    sockets: list[_FakePinnedSocket] = []
    resolutions = 0

    def resolver(*_args: object, **_kwargs: object):
        nonlocal resolutions
        resolutions += 1
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            ),
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("2606:4700:4700::1111", 443, 0, 0),
            ),
        ]

    def socket_factory(family: int, *_args: object):
        item: _FakePinnedSocket = (
            _FailingConnectSocket(clock)
            if family == socket.AF_INET
            else _FakePinnedSocket(response)
        )
        sockets.append(item)
        return item

    reader = OfficialGuidanceHTTPSReader(
        resolver=resolver,
        socket_factory=socket_factory,
        tls_context_factory=_FakeTLSContext,
        clock=clock,
        timeout_seconds=3.0,
    )

    material = reader.read(OFFICIAL_GUIDANCE_SOURCE_URL)

    assert material.content_text == "ipv4 success"
    assert resolutions == 1
    assert len(sockets) == 2
    assert sockets[0].closed is True
    assert sockets[1].closed is True
    assert sockets[1].connected_to == ("2606:4700:4700::1111", 443, 0, 0)
    assert sockets[1].timeout is not None and sockets[1].timeout <= 2.0


def test_pinned_reader_rejects_private_dns_before_connect() -> None:
    def resolver(*_args: object, **_kwargs: object):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443))]

    reader = OfficialGuidanceHTTPSReader(
        resolver=resolver,
        socket_factory=lambda *_args: pytest.fail("private address must not connect"),
    )

    with pytest.raises(OfficialGuidanceReadError) as error:
        reader.read(OFFICIAL_GUIDANCE_SOURCE_URL)

    assert error.value.code == "official_guidance_transport_unsafe_address"


@pytest.mark.parametrize(
    ("response", "expected_code"),
    [
        (
            b"HTTP/1.1 302 Found\r\nLocation: https://attacker.test/\r\n"
            b"Content-Length: 0\r\n\r\n",
            "official_guidance_redirect_rejected",
        ),
        (
            b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
            b"Content-Length: 2097153\r\n\r\n",
            "official_guidance_response_too_large",
        ),
    ],
)
def test_pinned_reader_rejects_redirects_and_oversize(
    response: bytes, expected_code: str
) -> None:
    reader, _sockets, _contexts = _fake_reader(response)

    with pytest.raises(OfficialGuidanceReadError) as error:
        reader.read(OFFICIAL_GUIDANCE_SOURCE_URL)

    assert error.value.code == expected_code


def test_pinned_reader_rejects_non_candidate_url_before_dns() -> None:
    resolved = False

    def resolver(*_args: object, **_kwargs: object):
        nonlocal resolved
        resolved = True
        return []

    reader = OfficialGuidanceHTTPSReader(resolver=resolver)
    with pytest.raises(OfficialGuidanceReadError) as error:
        reader.read(f"{OFFICIAL_GUIDANCE_SOURCE_URL}?redirect=1")

    assert error.value.code == "official_guidance_lineage_mismatch"
    assert resolved is False


def test_pinned_reader_ignores_repeated_irrelevant_set_cookie_headers() -> None:
    body = b"<html><body>safe</body></html>"
    response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n"
        b"Set-Cookie: first=1\r\n"
        b"Set-Cookie: second=2\r\n"
        + f"Content-Length: {len(body)}\r\n\r\n".encode()
        + body
    )
    reader, _sockets, _contexts = _fake_reader(response)

    material = reader.read(OFFICIAL_GUIDANCE_SOURCE_URL)

    assert material.content_text == "safe"


class _FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


class _EndlessTrailerSocket(_FakePinnedSocket):
    def __init__(self, clock: _FakeClock, *, advance_clock: bool) -> None:
        super().__init__(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n"
            b"0\r\n"
        )
        self._clock = clock
        self._advance_clock = advance_clock

    def recv(self, size: int) -> bytes:
        if self._response:
            return super().recv(size)
        if self._advance_clock:
            self._clock.value += 1.0
        return b"X-Trailer: keep-alive\r\n"


def _endless_trailer_reader(
    clock: _FakeClock, *, max_response_bytes: int, advance_clock: bool
):
    sockets: list[_EndlessTrailerSocket] = []
    contexts: list[_FakeTLSContext] = []

    def resolver(*_args: object, **_kwargs: object):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            )
        ]

    def socket_factory(*_args: object):
        item = _EndlessTrailerSocket(clock, advance_clock=advance_clock)
        sockets.append(item)
        return item

    def context_factory():
        item = _FakeTLSContext()
        contexts.append(item)
        return item

    return OfficialGuidanceHTTPSReader(
        resolver=resolver,
        socket_factory=socket_factory,
        tls_context_factory=context_factory,
        clock=clock,
        timeout_seconds=2.0,
        max_response_bytes=max_response_bytes,
    )


def test_pinned_reader_caps_cumulative_chunk_trailer_wire_bytes() -> None:
    clock = _FakeClock()
    reader = _endless_trailer_reader(
        clock, max_response_bytes=512, advance_clock=False
    )

    with pytest.raises(OfficialGuidanceReadError) as error:
        reader.read(OFFICIAL_GUIDANCE_SOURCE_URL)

    assert error.value.code == "official_guidance_response_too_large"


def test_pinned_reader_applies_one_deadline_across_endless_trailers() -> None:
    clock = _FakeClock()
    reader = _endless_trailer_reader(
        clock, max_response_bytes=1024 * 1024, advance_clock=True
    )

    with pytest.raises(OfficialGuidanceReadError) as error:
        reader.read(OFFICIAL_GUIDANCE_SOURCE_URL)

    assert error.value.code == "official_guidance_deadline_exceeded"


class _OfficialResearcher:
    def __init__(self) -> None:
        self.requests: list[object] = []

    def run_structured_turn(self, request: object) -> CodexAppServerTurnResult:
        self.requests.append(request)
        context = json.loads(request.application_context)
        observation_id = context["allowed_observation_ids"][0]
        return CodexAppServerTurnResult(
            status="completed",
            output_text=json.dumps(
                {
                    "proposed_claim": (
                        "ISO 37301 is a current international compliance management "
                        "systems standard."
                    ),
                    "scope": "ISO 37301 — compliance management systems",
                    "observation_ids": [observation_id],
                    "contradictions": [],
                    "unknowns": [],
                }
            ),
            turn_id="official-guidance-test-turn",
        )


def test_public_official_guidance_acquisition_and_research_are_review_only(
    tmp_path, monkeypatch
) -> None:
    workflow_store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    workflow_store.record_production_classification(exact_public_bdo_run())
    stored_identity = workflow_store.record_content_delivery_identity(
        identity_command(retained=True).model_copy(
            update={"retained_work_item_id": None, "retained_usage": None}
        )
    ).binding
    identity_candidate = stored_identity.model_copy(
        update={
            "canonical_path": OFFICIAL_GUIDANCE_CANONICAL_PATH,
            "public_url": "https://www.ekologus.pl" + OFFICIAL_GUIDANCE_CANONICAL_PATH,
        }
    )
    identity_payload = identity_candidate.model_dump(mode="json")
    identity_payload["binding_digest"] = content_delivery_identity_digest(identity_payload)
    identity_payload["binding_id"] = (
        f"content_delivery_identity_{content_delivery_identity_logical_id(identity_payload)[:24]}"
    )
    identity = ContentDeliveryIdentityBinding.model_validate(identity_payload)
    classification = workflow_store.load_production_classification_for_work_item(
        identity.current_work_item_id
    )
    assert classification is not None
    row_payload = classification.row.model_dump(mode="python")
    row_payload.update(
        {
            "canonical_path": OFFICIAL_GUIDANCE_CANONICAL_PATH,
            "public_url": identity.public_url,
            "decision": "refresh",
            "revision_approved": False,
            "revision_complete": False,
            "retained_work_item_id": None,
            "revision_id": None,
            "revision_digest": None,
            "retained_binding": None,
            "verified_actions": (),
            "verified_drafts": (),
        }
    )
    classification = ContentProductionClassificationProjection(
        run_id=classification.run_id,
        run_digest=classification.run_digest,
        decision_set_digest=classification.decision_set_digest,
        freshness=classification.freshness,
        row=ContentProductionClassificationRow.model_validate(row_payload),
    )
    read_at = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    adapter = OfficialGuidanceObservationAdapter(
        material_reader=lambda url: SimpleNamespace(
            url=url,
            content_text=(
                "ISO 37301 is an international standard for compliance management "
                "systems. It applies to organizations of any size."
            ),
            extraction_region="controlled_iso_reader.body",
        ),
        clock=lambda: read_at,
    )
    coordinator = EvidenceAcquisitionCoordinator(
        identity_loader=lambda _binding_id: identity,
        classification_loader=lambda _work_item_id: classification,
        store=workflow_store,
        official_guidance_snapshot_reader=adapter.read,
        clock=lambda: read_at,
    )
    command = EvidenceAcquisitionStartCommand(
        subject={
            "subject_kind": "identity_binding",
            "identity_binding_id": identity.binding_id,
        },
        research_question="Jaki zakres ma ISO 37301?",
        source_intent="official_primary",
        source_selector={
            "selector_kind": "official_primary",
            "candidate_id": OFFICIAL_GUIDANCE_CANDIDATE_ID,
        },
    )
    monkeypatch.setattr(
        acquisition_router,
        "build_default_evidence_acquisition_coordinator",
        lambda: coordinator,
    )
    researcher = _OfficialResearcher()
    research = EvidenceResearchCoordinator(
        acquisition_reader=coordinator.read,
        proposal_store=workflow_store,
        researcher=researcher,
        clock=lambda: read_at,
    )
    monkeypatch.setattr(
        acquisition_router,
        "build_default_evidence_research_coordinator",
        lambda: research,
    )

    with TestClient(app) as client:
        acquisition = client.post(
            "/api/content/evidence-acquisition", json=command.model_dump(mode="json")
        )
        assert acquisition.status_code == 200, acquisition.text
        run_payload = acquisition.json()
        assert run_payload["recorded_run"]["status"] == "ready_for_researcher"
        assert run_payload["recorded_run"]["observation"]["source_type"] == (
            "official_guidance_observation"
        )
        assert run_payload["recorded_run"]["observation"]["source_url"] == (
                    "https://committee.iso.org/sites/tc309/home/projects/published/"
                    "iso-37301-compliance-management.html"
        )
        run_id = run_payload["run_id"]
        repeated = client.post(
            "/api/content/evidence-acquisition", json=command.model_dump(mode="json")
        )
        assert repeated.status_code == 200
        assert repeated.json()["run_id"] == run_id

        proposal = client.post(f"/api/content/evidence-acquisition/{run_id}/research")
        assert proposal.status_code == 200, proposal.text
        proposal_payload = proposal.json()
        assert proposal_payload["current_status"] == "ready_for_review"
        request = researcher.requests[0]
        assert request.output_schema["properties"]["scope"]["enum"] == [
            "ISO 37301 — compliance management systems",
        ]
        request_context = json.loads(request.application_context)
        assert request_context["official_guidance_candidate"]["scope_label"] == (
            "ISO 37301 — compliance management systems"
        )
        proposal_id = proposal_payload["proposal_id"]
        readback = client.get(
            f"/api/content/evidence-acquisition/research/{proposal_id}"
        )
        assert readback.status_code == 200
        readback_payload = readback.json()
        assert readback_payload["recorded_proposal"]["approved"] is False
        assert readback_payload["recorded_proposal"]["review_required"] is True
        assert readback_payload["recorded_proposal"]["source_url"] == (
            "https://committee.iso.org/sites/tc309/home/projects/published/"
            "iso-37301-compliance-management.html"
        )
        assert "secret" not in json.dumps(readback_payload).casefold()
