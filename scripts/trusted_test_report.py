#!/usr/bin/env python3
"""Emit a bounded, phase-aware pytest report for the change-contract gate.

The checker invokes this module by its canonical absolute path with Python's
isolated mode.  It is deliberately small: candidate code is imported only
after the snapshot has been placed on ``sys.path`` and no candidate config or
third-party plugin is allowed to alter the report shape.
"""

from __future__ import annotations

import argparse
import importlib.abc
import importlib.machinery
import json
import os
import sys
import sysconfig
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

try:
    import pytest
except ModuleNotFoundError:
    python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    virtualenv_root = Path(sys.executable).parent.parent
    dependency_paths = (
        virtualenv_root / "lib" / python_version / "site-packages",
        virtualenv_root / "Lib" / "site-packages",
        Path(sysconfig.get_paths().get("purelib", "")),
        Path(sysconfig.get_paths().get("platlib", "")),
    )
    for package_path in dependency_paths:
        package_path_string = str(package_path)
        if package_path_string and package_path_string not in sys.path:
            sys.path.append(package_path_string)
    import pytest

_MAX_CASES = 4096
_ASSERTION_TYPES = frozenset({"AssertionError", "Failed"})


class _ReportPlugin:
    def __init__(self) -> None:
        self.collection_errors = 0
        self.internal_errors = 0
        self.setup_failures = 0
        self.teardown_failures = 0
        self.call_assertion_failures = 0
        self.call_non_assertion_failures = 0
        self.cases: list[dict[str, Any]] = []
        self.overflow = False
        self.tests_collected = 0
        self.exit_status: int | None = None

    @pytest.hookimpl
    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.tests_collected = session.testscollected

    @pytest.hookimpl
    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.failed:
            self.collection_errors += 1

    @pytest.hookimpl
    def pytest_internalerror(self, excrepr: Any, excinfo: Any) -> None:
        del excrepr, excinfo
        self.internal_errors += 1

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(
        self,
        item: pytest.Item,
        call: pytest.CallInfo[Any],
    ) -> Any:
        outcome = yield
        report = outcome.get_result()
        if len(self.cases) >= _MAX_CASES:
            self.overflow = True
            return
        if report.when == "setup" and report.failed:
            self.setup_failures += 1
        elif report.when == "teardown" and report.failed:
            self.teardown_failures += 1
        elif report.when == "call" and report.failed:
            typename = call.excinfo.typename if call.excinfo is not None else ""
            if typename in _ASSERTION_TYPES or (
                call.excinfo is not None
                and call.excinfo.errisinstance(AssertionError)
            ):
                self.call_assertion_failures += 1
            else:
                self.call_non_assertion_failures += 1
        self.cases.append(
            {
                "nodeid": item.nodeid,
                "when": report.when,
                "outcome": report.outcome,
                "assertion": bool(
                    report.when == "call"
                    and report.failed
                    and call.excinfo is not None
                    and (
                        call.excinfo.typename in _ASSERTION_TYPES
                        or call.excinfo.errisinstance(AssertionError)
                    )
                ),
            }
        )

    @pytest.hookimpl
    def pytest_sessionfinish(
        self,
        session: pytest.Session,
        exitstatus: int,
    ) -> None:
        if self.tests_collected == 0:
            self.tests_collected = len(
                {case["nodeid"] for case in self.cases if "nodeid" in case}
            )
        self.exit_status = int(exitstatus)


def _repository_names(root: Path) -> set[str]:
    names: set[str] = set()
    for entry in root.iterdir():
        if entry.name.startswith("."):
            continue
        if entry.is_dir() or entry.suffix == ".py":
            names.add(entry.stem if entry.is_file() else entry.name)
    return names


def _origin_within(origin: str | None, root: Path) -> bool:
    if not origin or origin in {"built-in", "frozen"}:
        return True
    try:
        Path(origin).resolve(strict=False).relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _repository_origin_errors(root: Path) -> int:
    names = _repository_names(root)
    errors = 0
    for module_name, module in tuple(sys.modules.items()):
        top_level = module_name.partition(".")[0]
        if top_level not in names:
            continue
        origin = getattr(module, "__file__", None)
        if not isinstance(origin, str):
            spec = getattr(module, "__spec__", None)
            origin = getattr(spec, "origin", None)
        if not _origin_within(origin, root):
            errors += 1
            continue
        spec = getattr(module, "__spec__", None)
        locations = getattr(spec, "submodule_search_locations", None)
        if locations is not None and any(
            not _origin_within(str(location), root) for location in locations
        ):
            errors += 1
    return errors


class _SnapshotImportGuard(importlib.abc.MetaPathFinder):
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.names = _repository_names(self.root)

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        del target
        top_level = fullname.partition(".")[0]
        if top_level not in self.names:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None:
            raise ModuleNotFoundError(
                f"repository module {fullname!r} is absent from snapshot"
            )
        origin = getattr(spec, "origin", None)
        if not _origin_within(origin, self.root):
            raise ImportError(f"repository module {fullname!r} escaped snapshot")
        locations = getattr(spec, "submodule_search_locations", None)
        if locations is not None and any(
            not _origin_within(str(location), self.root) for location in locations
        ):
            raise ImportError(f"repository package {fullname!r} escaped snapshot")
        return spec

def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _isolate_imports(root: Path) -> None:
    root = root.resolve()
    helper_root = Path(__file__).resolve().parent
    canonical_root = helper_root.parent
    kept: list[str] = []
    for entry in sys.path:
        if not entry:
            continue
        try:
            resolved = Path(entry).resolve()
        except OSError:
            continue
        if _is_within(resolved, helper_root) or (
            _is_within(resolved, canonical_root)
            and "site-packages" not in resolved.parts
        ):
            continue
        kept.append(entry)
    sys.path[:] = [str(root), *kept]


def _write_report(
    path: Path,
    plugin: _ReportPlugin,
    pytest_status: int,
    origin_errors: int,
) -> None:
    payload = {
        "version": 1,
        "pytest_status": int(pytest_status),
        "tests_collected": plugin.tests_collected,
        "collection_errors": plugin.collection_errors,
        "internal_errors": plugin.internal_errors,
        "setup_failures": plugin.setup_failures,
        "teardown_failures": plugin.teardown_failures,
        "call_assertion_failures": plugin.call_assertion_failures,
        "call_non_assertion_failures": plugin.call_non_assertion_failures,
        "overflow": plugin.overflow,
        "origin_errors": origin_errors,
        "cases": plugin.cases[:_MAX_CASES],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=argv[0])
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--report-file", required=True, type=Path)
    parser.add_argument("selectors", nargs="+")
    arguments = parser.parse_args(argv[1:])
    root = arguments.root.resolve()
    if not root.is_dir():
        return 2
    _isolate_imports(root)
    import_guard = _SnapshotImportGuard(root)
    sys.meta_path.insert(0, import_guard)
    os.chdir(root)
    config_path = root / ".changes-check-pytest.ini"
    config_path.write_text("[pytest]\n", encoding="utf-8")
    plugin = _ReportPlugin()
    status = 2
    origin_errors = 0
    try:
        status = int(
            pytest.main(
                [
                    "-c",
                    str(config_path),
                    "--color=no",
                    "--tb=short",
                    *arguments.selectors,
                ],
                plugins=[plugin],
            )
        )
    except BaseException:
        plugin.internal_errors += 1
    finally:
        sys.meta_path.remove(import_guard)
        origin_errors = _repository_origin_errors(root)
        if origin_errors:
            plugin.internal_errors += origin_errors
        _write_report(arguments.report_file.resolve(), plugin, status, origin_errors)
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
