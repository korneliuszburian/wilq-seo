from __future__ import annotations

import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STACK_SCRIPT = ROOT / "scripts" / "local_stack.sh"


def test_local_stack_script_is_executable_and_valid_bash() -> None:
    assert STACK_SCRIPT.exists()
    assert os.access(STACK_SCRIPT, os.X_OK)

    result = subprocess.run(
        ["bash", "-n", str(STACK_SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_local_stack_help_documents_operator_commands() -> None:
    result = subprocess.run(
        [str(STACK_SCRIPT), "--help"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "start|stop|restart|status|logs" in result.stdout
    assert "http://127.0.0.1:8000" in result.stdout
    assert "http://127.0.0.1:5173/command-center" in result.stdout


def test_local_stack_rejects_non_loopback_bind_before_running_command(tmp_path: Path) -> None:
    for index, host_overrides in enumerate(
        (
            {"WILQ_API_HOST": "0.0.0.0", "WILQ_DASHBOARD_HOST": "127.0.0.1"},
            {"WILQ_API_HOST": "127.0.0.1", "WILQ_DASHBOARD_HOST": "0.0.0.0"},
        )
    ):
        runtime_dir = tmp_path / f"runtime-{index}"
        environment = {
            **os.environ,
            "WILQ_RUNTIME_DIR": str(runtime_dir),
            **host_overrides,
        }

        result = subprocess.run(
            [str(STACK_SCRIPT), "status"],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 2
        assert "refusing non-loopback bind" in result.stderr
        assert not runtime_dir.exists()


def test_local_stack_normalizes_runtime_directory_and_file_modes(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(mode=0o755)
    pid_file = runtime_dir / "api.pid"
    log_file = runtime_dir / "api.log"
    port_file = runtime_dir / "dashboard.port"
    pid_file.write_text("", encoding="utf-8")
    log_file.write_text("", encoding="utf-8")
    port_file.write_text("5188\n", encoding="utf-8")
    pid_file.chmod(0o644)
    log_file.chmod(0o644)
    port_file.chmod(0o644)

    result = subprocess.run(
        [str(STACK_SCRIPT), "status"],
        cwd=ROOT,
        env={**os.environ, "WILQ_RUNTIME_DIR": str(runtime_dir)},
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert runtime_dir.stat().st_mode & 0o777 == 0o700
    assert pid_file.stat().st_mode & 0o777 == 0o600
    assert log_file.stat().st_mode & 0o777 == 0o600
    assert port_file.stat().st_mode & 0o777 == 0o600


def test_local_stack_status_uses_recorded_port_for_live_dashboard(
    tmp_path: Path,
) -> None:
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.end_headers()

        def log_message(self, _format: str, *_args: object) -> None:
            return

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
    dashboard_port = server.server_address[1]
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    managed_process = subprocess.Popen(["sleep", "30"])
    try:
        (runtime_dir / "dashboard.pid").write_text(
            f"{managed_process.pid}\n",
            encoding="utf-8",
        )
        (runtime_dir / "dashboard.port").write_text(
            f"{dashboard_port}\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [str(STACK_SCRIPT), "status"],
            cwd=ROOT,
            env={**os.environ, "WILQ_RUNTIME_DIR": str(runtime_dir)},
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        managed_process.terminate()
        managed_process.wait(timeout=5)
        server.shutdown()
        server.server_close()

    assert result.returncode == 0, result.stderr
    dashboard_status = result.stdout.split("dashboard\n", maxsplit=1)[1]
    assert f"port_owner_pid: {os.getpid()}" in dashboard_status
    assert "ready: yes" in dashboard_status


def test_operator_docs_point_to_local_stack_manager() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    context = (ROOT / "docs" / "CONTEXT.md").read_text(encoding="utf-8")
    goal = (ROOT / "docs" / "goals" / "001-goal.md").read_text(encoding="utf-8")

    for content in (agents, context, goal):
        assert "scripts/local_stack.sh" in content
    assert "Do not hand-roll" in agents
