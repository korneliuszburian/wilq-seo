from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from wilq.codex import app_server_process as process


def _fixture(tmp_path: Path, monkeypatch: MonkeyPatch):
    wrapper = tmp_path / "codex"
    wrapper.write_text("#!/bin/bash\n# mise launcher\n")
    wrapper.chmod(0o700)
    mise = tmp_path / "mise"
    mise.write_text("#!/bin/sh\nexit 0\n")
    mise.chmod(0o700)
    data = tmp_path / "data"
    install = data / "installs" / "codex" / "0.160.0"
    candidate = install / "bin" / "codex"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("#!/bin/sh\nexit 0\n")
    candidate.chmod(0o700)
    monkeypatch.setenv("MISE_DATA_DIR", str(data))
    monkeypatch.setenv("HOME", str(tmp_path / "operator-home"))
    monkeypatch.setenv("CODEX_API_KEY", "synthetic-only")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-only")
    monkeypatch.setenv("MISE_CONFIG_FILE", "synthetic-config")
    monkeypatch.setattr(
        process.shutil, "which", lambda name: str(wrapper if name == "codex" else mise)
    )
    row = {"installed": True, "version": "0.160.0", "install_path": str(install)}
    return wrapper, mise, data, candidate, row


@pytest.mark.parametrize("shebang", ["#!/bin/bash", "#!/bin/sh", "#!/usr/bin/env -S zsh -e"])
def test_neutral_lookup_selects_installed_version_without_operator_configuration(
    tmp_path: Path, monkeypatch: MonkeyPatch, shebang: str,
) -> None:
    wrapper, mise, data, candidate, row = _fixture(tmp_path, monkeypatch)
    wrapper.write_text(shebang + "\n# mise launcher\n")
    calls = []

    def lookup(args, **kwargs):
        assert args[0] == str(mise.resolve())
        environment = kwargs["env"]
        assert environment["MISE_NO_CONFIG"] == "1"
        assert environment["MISE_OFFLINE"] == "1"
        assert environment["MISE_AUTO_INSTALL"] == "0"
        assert environment["MISE_DATA_DIR"] == str(data)
        assert environment["HOME"] != os.environ["HOME"]
        assert not {"CODEX_API_KEY", "OPENAI_API_KEY", "MISE_CONFIG_FILE"} & environment.keys()
        cwd = Path(kwargs["cwd"])
        assert cwd.exists() and cwd != Path.cwd()
        assert not (cwd / ".mise.toml").exists()
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert 0 < kwargs["timeout"] <= 10
        calls.append((args, kwargs["timeout"], cwd))
        output = json.dumps([row]) if args[1] == "ls" else str(candidate)
        return subprocess.CompletedProcess(args, 0, output)

    monkeypatch.setattr(process.subprocess, "run", lookup)
    assert process._resolve_codex_executable() == str(candidate.resolve())
    assert calls[0][0][1:] == ["ls", "--installed", "--json", "codex"]
    assert calls[1][0][1:] == ["which", "codex", "--tool", "codex@0.160.0"]
    assert calls[1][1] <= calls[0][1]
    assert not calls[0][2].exists()
    assert str(wrapper) != str(candidate)


@pytest.mark.parametrize("fault", [
    "timeout", "os_error", "nonzero", "malformed", "empty", "uninstalled",
    "nonnumeric", "foreign_install", "relative_install", "relative_candidate",
    "non_executable", "directory", "escaping_symlink", "oversized",
])
def test_failed_lookup_never_runs_original_launcher(
    tmp_path: Path, monkeypatch: MonkeyPatch, fault: str,
) -> None:
    _, _, _, candidate, row = _fixture(tmp_path, monkeypatch)
    if fault == "uninstalled":
        row["installed"] = False
    if fault == "nonnumeric":
        row["version"] = "latest"
    if fault == "foreign_install":
        row["install_path"] = str(tmp_path)
    if fault == "relative_install":
        row["install_path"] = "relative"
    if fault == "non_executable":
        candidate.chmod(0o600)
    if fault == "directory":
        candidate.unlink()
        candidate.mkdir()
    if fault == "escaping_symlink":
        candidate.unlink()
        target = tmp_path / "foreign"
        target.write_text("#!/bin/sh\nexit 0\n")
        target.chmod(0o700)
        candidate.symlink_to(target)

    def lookup(args, **kwargs):
        if fault == "timeout":
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])
        if fault == "os_error":
            raise OSError("controlled failure")
        output = json.dumps([row]) if args[1] == "ls" else str(candidate)
        if args[1] == "ls" and fault == "malformed":
            output = "not JSON"
        if args[1] == "ls" and fault == "empty":
            output = "[]"
        if args[1] == "ls" and fault == "oversized":
            output = "x" * 65537
        if args[1] == "which" and fault == "relative_candidate":
            output = "relative"
        return subprocess.CompletedProcess(args, 1 if fault == "nonzero" else 0, output)

    monkeypatch.setattr(process.subprocess, "run", lookup)
    with pytest.raises(process.CodexAppServerProcessFailure) as caught:
        process._resolve_codex_executable()
    assert caught.value.code == "codex_not_available"


def test_latest_installed_numeric_release_is_selected_without_config(
    tmp_path: Path, monkeypatch: MonkeyPatch,
) -> None:
    _, _, data, _, row = _fixture(tmp_path, monkeypatch)
    newer = data / "installs" / "codex" / "0.161.0"
    newer.mkdir()
    version, install = process._installed_codex(json.dumps([
        row, {"installed": True, "version": "0.161.0", "install_path": str(newer)},
        {"installed": False, "version": "0.999.0", "install_path": "not-installed"},
    ]), data)
    assert version == "0.161.0"
    assert install == newer
