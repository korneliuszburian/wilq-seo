"""Private Git snapshot and path-validation primitives for change contracts."""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import subprocess
import tarfile
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path, PurePosixPath


class SnapshotError(Exception):
    """A Git object cannot be materialized as a safe test snapshot."""


INJECTION_ENVIRONMENT_KEYS = frozenset(
    {
        "BASH_ENV",
        "CDPATH",
        "ENV",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CEILING_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_SYSTEM",
        "GIT_CONFIG_VALUE_0",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_NO_REPLACE_OBJECTS",
        "GIT_OBJECT_DIRECTORY",
        "GIT_REPLACE_REF_BASE",
        "GIT_WORK_TREE",
        "NODE_OPTIONS",
        "PERL5OPT",
        "PYTHONBREAKPOINT",
        "PYTHONINSPECT",
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONSTARTUP",
        "PYTHONUSERBASE",
        "PYTHONWARNINGS",
        "PYTEST_ADDOPTS",
        "PYTEST_CURRENT_TEST",
        "PYTEST_PLUGINS",
        "RUBYOPT",
    }
)


def git_environment() -> dict[str, str]:
    return {
        "PATH": os.defpath,
        "LC_ALL": "C",
        "LANG": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1",
    }


def safe_relative_path(value: str) -> str:
    if (
        not value
        or "\\" in value
        or "\x00" in value
        or (len(value) > 1 and value[1] == ":")
    ):
        raise SnapshotError(f"unsafe path {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise SnapshotError(f"unsafe path {value!r}")
    normalized = path.as_posix()
    if normalized != value:
        raise SnapshotError(f"non-canonical path {value!r}")
    return normalized


def selector_path(selector: str) -> str:
    if not selector or selector.startswith("-") or "\x00" in selector:
        raise SnapshotError(f"unsafe pytest selector {selector!r}")
    path, separator, node = selector.partition("::")
    if separator and not node:
        raise SnapshotError(f"empty pytest node selector {selector!r}")
    return safe_relative_path(path)


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _tree_entries(repository_root: Path, commit: str) -> list[tuple[str, str]]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "--full-tree", commit],
        cwd=repository_root,
        check=False,
        capture_output=True,
        env=git_environment(),
    )
    if result.returncode != 0:
        raise SnapshotError(f"cannot inspect tree {commit}")
    entries: list[tuple[str, str]] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        header, separator, path_bytes = raw.partition(b"\t")
        if not separator:
            raise SnapshotError(f"malformed tree entry in {commit}")
        fields = header.split(b" ", 2)
        if len(fields) != 3:
            raise SnapshotError(f"malformed tree entry in {commit}")
        mode = fields[0].decode("ascii", errors="strict")
        path = path_bytes.decode("utf-8", errors="surrogateescape")
        entries.append((mode, safe_relative_path(path)))
    return entries


def archive_tree(repository_root: Path, commit: str, destination: Path) -> None:
    if any(mode == "160000" for mode, _ in _tree_entries(repository_root, commit)):
        raise SnapshotError("submodules are not valid change-contract inputs")
    result = subprocess.run(
        ["git", "archive", "--format=tar", commit],
        cwd=repository_root,
        check=False,
        capture_output=True,
        env=git_environment(),
    )
    if result.returncode != 0:
        raise SnapshotError(f"cannot materialize tree {commit}")
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with closing(tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:")) as archive:
            _extract_archive(archive, destination)
    except (tarfile.TarError, OSError) as error:
        raise SnapshotError("Git archive is unreadable") from error


def _extract_archive(archive: tarfile.TarFile, destination: Path) -> None:
    for member in archive.getmembers():
        relative = safe_relative_path(member.name.rstrip("/"))
        target = destination / relative
        if not _within(target, destination):
            raise SnapshotError(f"archive path escapes snapshot: {relative}")
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if member.issym():
            _extract_symlink(member, relative, target, destination)
            continue
        if not member.isreg():
            raise SnapshotError(f"unsupported Git archive entry: {relative}")
        source = archive.extractfile(member)
        if source is None:
            raise SnapshotError(f"missing Git archive entry: {relative}")
        with source, target.open("wb") as stream:
            shutil.copyfileobj(source, stream)
        target.chmod(member.mode & 0o777)


def _extract_symlink(
    member: tarfile.TarInfo,
    relative: str,
    target: Path,
    destination: Path,
) -> None:
    if PurePosixPath(relative).name != "CLAUDE.md":
        raise SnapshotError("only a contained CLAUDE.md symlink is allowed")
    link_target = (target.parent / member.linkname).resolve(strict=False)
    if not _within(link_target, destination):
        raise SnapshotError(f"symlink escapes snapshot: {relative}")
    target.symlink_to(member.linkname)


def snapshot_path(snapshot: Path, relative: str) -> Path:
    relative = safe_relative_path(relative)
    path = snapshot / relative
    if not _within(path, snapshot):
        raise SnapshotError(f"path escapes snapshot: {relative}")
    for parent in [snapshot / part for part in PurePosixPath(relative).parents if str(part) != "."]:
        if parent != snapshot and parent.is_symlink():
            raise SnapshotError(f"observer path traverses symlink: {relative}")
    if path.is_symlink():
        if PurePosixPath(relative).name != "CLAUDE.md":
            raise SnapshotError(f"observer symlink is not allowed: {relative}")
        if not _within(path.resolve(strict=False), snapshot):
            raise SnapshotError(f"observer symlink escapes snapshot: {relative}")
    return path


def observer_signature(snapshot: Path, relative: str) -> str:
    path = snapshot_path(snapshot, relative)
    try:
        stat = path.lstat()
    except OSError as error:
        raise SnapshotError(f"observer path is absent: {relative}") from error
    if path.is_symlink():
        return _symlink_signature(path, snapshot, set())
    if not path.is_file() or not stat:
        raise SnapshotError(f"observer path is not a file: {relative}")
    return _file_signature(path)


def _symlink_signature(path: Path, root: Path, seen: set[Path]) -> str:
    if path in seen:
        raise SnapshotError(f"symlink cycle in observer: {path}")
    if path.name != "CLAUDE.md":
        raise SnapshotError(f"observer symlink is not allowed: {path}")
    try:
        link_text = os.readlink(path)
        target = path.parent / link_text
        target.lstat()
    except (OSError, RuntimeError) as error:
        raise SnapshotError(f"observer symlink target is unreadable: {path}") from error
    if not _within(target, root):
        raise SnapshotError(f"observer symlink escapes snapshot: {path}")
    nested_seen = {*seen, path}
    if target.is_symlink():
        target_signature = _symlink_signature(target, root, nested_seen)
    else:
        if not target.is_file():
            raise SnapshotError(f"observer symlink target is not a file: {path}")
        target_signature = _file_signature(target)
    return f"symlink:{link_text}:target:{target_signature}"


def _file_signature(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"file:{digest.hexdigest()}"


def overlay_observers(
    parent_snapshot: Path,
    candidate_snapshot: Path,
    observer_paths: Sequence[str],
) -> None:
    for relative in observer_paths:
        source = snapshot_path(candidate_snapshot, relative)
        observer_signature(candidate_snapshot, relative)
        destination = parent_snapshot / relative
        if destination.exists() or destination.is_symlink():
            _replace_target(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            destination.symlink_to(os.readlink(source))
        else:
            shutil.copy2(source, destination)


def _replace_target(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
