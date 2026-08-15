from __future__ import annotations

import os
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEALTH_CHECK_SCRIPT = ROOT / "scripts" / "health_check.sh"
PRIVATE_RESPONSE_MARKER = "testowa-wartosc-poufna"


class HealthyWILQHandler(BaseHTTPRequestHandler):
    health_body = b'{\n  "service": "wilq-api",\n  "status": "ok"\n}'
    system_body = (
        b'{"runtime":"ready","private_field":"testowa-wartosc-poufna"}'
    )
    system_status = HTTPStatus.OK

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/health":
            self._respond(HTTPStatus.OK, self.health_body)
            return
        if self.path == "/api/system/status":
            self._respond(self.system_status, self.system_body)
            return
        self._respond(HTTPStatus.NOT_FOUND, b'{"detail":"not found"}')

    def _respond(self, status: HTTPStatus, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


class UnhealthyWILQHandler(HealthyWILQHandler):
    health_body = (
        b'{"status":"degraded","private_field":"testowa-wartosc-poufna"}'
    )


class NonJsonHealthHandler(HealthyWILQHandler):
    health_body = b'not-json "status":"ok"'


class NestedHealthStatusHandler(HealthyWILQHandler):
    health_body = b'{"runtime":{"status":"ok"}}'


class MissingSystemStatusHandler(HealthyWILQHandler):
    system_status = HTTPStatus.NOT_FOUND


class NonOkSystemStatusHandler(HealthyWILQHandler):
    system_body = b""
    system_status = HTTPStatus.NO_CONTENT


@contextmanager
def stub_server(handler: type[BaseHTTPRequestHandler]) -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        assert not thread.is_alive()


def run_health_check(base_url: str) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "NO_PROXY": "127.0.0.1,localhost",
        "WILQ_HEALTH_BASE_URL": base_url,
        "no_proxy": "127.0.0.1,localhost",
    }
    return subprocess.run(
        [str(HEALTH_CHECK_SCRIPT)],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_health_check_script_contract() -> None:
    assert HEALTH_CHECK_SCRIPT.exists()
    assert os.access(HEALTH_CHECK_SCRIPT, os.X_OK)
    script = HEALTH_CHECK_SCRIPT.read_text(encoding="utf-8")
    assert "set -euo pipefail" in script
    assert "WILQ_HEALTH_BASE_URL" in script
    assert "http://127.0.0.1:8000" in script
    assert "curl" in script
    for option in (
        "--disable",
        "--globoff",
        "--fail",
        "--silent",
        "--show-error",
        "--max-time 10",
        "--url",
    ):
        assert option in script


def test_health_check_succeeds_when_required_endpoints_are_healthy() -> None:
    with stub_server(HealthyWILQHandler) as base_url:
        result = run_health_check(base_url)

    assert result.returncode == 0, result.stderr
    assert PRIVATE_RESPONSE_MARKER not in result.stdout + result.stderr


def test_health_check_rejects_non_ok_health_status_with_polish_error() -> None:
    with stub_server(UnhealthyWILQHandler) as base_url:
        result = run_health_check(base_url)

    assert result.returncode != 0
    assert "/api/health" in result.stderr
    assert "statusu ok" in result.stderr
    assert PRIVATE_RESPONSE_MARKER not in result.stdout + result.stderr


def test_health_check_rejects_non_json_or_nested_health_status() -> None:
    for handler in (NonJsonHealthHandler, NestedHealthStatusHandler):
        with stub_server(handler) as base_url:
            result = run_health_check(base_url)

        assert result.returncode != 0
        assert "/api/health" in result.stderr
        assert "statusu ok" in result.stderr


def test_health_check_reports_system_status_failure_in_polish() -> None:
    with stub_server(MissingSystemStatusHandler) as base_url:
        result = run_health_check(base_url)

    assert result.returncode != 0
    assert "/api/system/status" in result.stderr
    assert "BŁĄD" in result.stderr


def test_health_check_requires_exact_http_200_for_system_status() -> None:
    with stub_server(NonOkSystemStatusHandler) as base_url:
        result = run_health_check(base_url)

    assert result.returncode != 0
    assert "/api/system/status" in result.stderr
    assert "HTTP 200" in result.stderr
