from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = ROOT / "deploy"
API_UNIT = DEPLOY_DIR / "wilq-api.service"
DASHBOARD_UNIT = DEPLOY_DIR / "wilq-dashboard.service"
UNIT_PATHS = (API_UNIT, DASHBOARD_UNIT)
REQUIRED_SERVICE_DIRECTIVES = {
    "EnvironmentFile=-/opt/wilq/.env",
    "Environment=WILQ_API_RELOAD=0",
    "Restart=always",
    "RestartSec=3",
    "UMask=0077",
    "ProtectSystem=strict",
    "ReadWritePaths=/opt/wilq/.local-lab/state /opt/wilq/.local-lab/backup",
    "NoNewPrivileges=true",
    "PrivateTmp=true",
}


def test_deploy_units_exist_and_are_not_executable() -> None:
    for unit_path in UNIT_PATHS:
        assert unit_path.is_file()
        assert unit_path.stat().st_mode & 0o111 == 0

        service = _section(unit_path, "Service")
        assert REQUIRED_SERVICE_DIRECTIVES.issubset(service)
        exec_start = next(line for line in service if line.startswith("ExecStart="))
        assert " --host 127.0.0.1 --port 8000" in exec_start
        assert "--reload" not in exec_start


def test_api_unit_has_restart_contract_and_marked_path_placeholder() -> None:
    unit = API_UNIT.read_text(encoding="utf-8")
    service = _section(API_UNIT, "Service")

    assert "Restart=always" in service
    assert "RestartSec=3" in service
    assert "Environment=WILQ_API_RELOAD=0" in service
    assert "WorkingDirectory=/opt/wilq" in service
    assert "# TEMPLATE:" in unit
    assert str(ROOT) not in unit


def test_dashboard_unit_is_an_alternative_api_process_with_built_spa() -> None:
    api_unit = API_UNIT.read_text(encoding="utf-8")
    dashboard_unit = DASHBOARD_UNIT.read_text(encoding="utf-8")
    dashboard_service = _section(DASHBOARD_UNIT, "Service")

    dashboard_unit_directives = _section(DASHBOARD_UNIT, "Unit")
    assert "Conflicts=wilq-api.service" in dashboard_unit_directives
    assert (
        "AssertPathIsDirectory=/opt/wilq/apps/dashboard/dist" in dashboard_unit_directives
    )
    assert "Environment=WILQ_SERVE_DASHBOARD=1" in dashboard_service
    assert (
        "Environment=WILQ_DASHBOARD_DIST=/opt/wilq/apps/dashboard/dist"
        in dashboard_service
    )
    assert "Preferowane wdrożenie: wilq-api.service" in dashboard_unit
    assert _exec_start(dashboard_unit) == _exec_start(api_unit)


def test_deploy_units_do_not_embed_secret_looking_values() -> None:
    units = "\n".join(path.read_text(encoding="utf-8") for path in UNIT_PATHS).casefold()

    for forbidden in ("password=", "token=", "secret=", "api_key=", "sk-", "akia"):
        assert forbidden not in units


def _exec_start(unit: str) -> str:
    return next(line for line in unit.splitlines() if line.startswith("ExecStart="))


def _section(unit_path: Path, name: str) -> set[str]:
    directives: set[str] = set()
    current_section: str | None = None
    for raw_line in unit_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1]
        elif current_section == name and line and not line.startswith("#"):
            directives.add(line)
    return directives
