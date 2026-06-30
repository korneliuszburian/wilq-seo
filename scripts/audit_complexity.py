from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

EXCLUDED_DIRS = {
    ".beads",
    ".git",
    ".local-lab",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
}

FROZEN_GROWTH_FILES = {
    Path("apps/api/wilq_api/main.py"),
    Path("wilq/schemas.py"),
    Path("wilq/actions/service.py"),
    Path("wilq/briefing/content_diagnostics.py"),
    Path("tests/test_api_contracts.py"),
    Path("apps/dashboard/src/routes/ContentDiagnosticSurface.tsx"),
}

BRANCH_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.ExceptHandler,
    ast.IfExp,
    ast.BoolOp,
    ast.Match,
)


@dataclass(frozen=True)
class FileMetric:
    path: Path
    loc: int


@dataclass(frozen=True)
class CodeBlockMetric:
    path: Path
    name: str
    line: int
    lines: int
    branch_count: int


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.class_stack: list[str] = []
        self.functions: list[CodeBlockMetric] = []
        self.classes: list[CodeBlockMetric] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        name = ".".join([*self.class_stack, node.name])
        self.classes.append(
            CodeBlockMetric(
                path=self.path,
                name=name,
                line=node.lineno,
                lines=node_lines(node),
                branch_count=branch_count(node),
            )
        )
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_function(node)
        self.generic_visit(node)

    def _record_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        name = ".".join([*self.class_stack, node.name])
        self.functions.append(
            CodeBlockMetric(
                path=self.path,
                name=name,
                line=node.lineno,
                lines=node_lines(node),
                branch_count=branch_count(node),
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report Python complexity hotspots and frozen-file growth risk for "
            "WILQ long-running goals."
        )
    )
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print the markdown summary. This is the default mode.",
    )
    parser.add_argument(
        "--changed",
        action="store_true",
        help="Fail if changed files include frozen growth areas.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum rows per hotspot section.",
    )
    parser.add_argument(
        "--allow-frozen",
        action="store_true",
        help="Do not fail --changed when frozen growth files changed.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files, functions, classes = collect_metrics(root)
    changed = changed_files(root)
    frozen_changed = sorted(path for path in changed if path in FROZEN_GROWTH_FILES)

    print(render_summary(root, files, functions, classes, changed, frozen_changed, args.limit))

    if args.changed and frozen_changed and not args.allow_frozen:
        print(
            "\nFrozen growth files changed. Move new behavior into domain modules "
            "or rerun with --allow-frozen for a documented extraction slice.",
            file=sys.stderr,
        )
        return 1
    return 0


def collect_metrics(
    root: Path,
) -> tuple[list[FileMetric], list[CodeBlockMetric], list[CodeBlockMetric]]:
    files: list[FileMetric] = []
    functions: list[CodeBlockMetric] = []
    classes: list[CodeBlockMetric] = []

    for path in iter_python_files(root):
        relative_path = path.relative_to(root)
        source = path.read_text(encoding="utf-8")
        files.append(FileMetric(path=relative_path, loc=count_code_lines(source)))
        try:
            tree = ast.parse(source, filename=str(relative_path))
        except SyntaxError:
            continue
        visitor = ComplexityVisitor(relative_path)
        visitor.visit(tree)
        functions.extend(visitor.functions)
        classes.extend(visitor.classes)

    return files, functions, classes


def iter_python_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        paths.append(path)
    return sorted(paths)


def count_code_lines(source: str) -> int:
    return sum(1 for line in source.splitlines() if line.strip())


def node_lines(node: ast.AST) -> int:
    start = getattr(node, "lineno", 0)
    end = getattr(node, "end_lineno", start)
    return max(0, end - start + 1)


def branch_count(node: ast.AST) -> int:
    total = 0
    for child in ast.walk(node):
        if isinstance(child, BRANCH_NODES):
            total += 1
        elif isinstance(child, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
            total += sum(len(generator.ifs) for generator in child.generators)
    return total


def changed_files(root: Path) -> set[Path]:
    changed = set(run_git_paths(root, ["diff", "--name-only", "HEAD", "--"]))
    changed.update(run_git_paths(root, ["ls-files", "--others", "--exclude-standard"]))
    return {Path(path) for path in changed}


def run_git_paths(root: Path, args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def render_summary(
    root: Path,
    files: list[FileMetric],
    functions: list[CodeBlockMetric],
    classes: list[CodeBlockMetric],
    changed: set[Path],
    frozen_changed: list[Path],
    limit: int,
) -> str:
    python_loc = sum(file.loc for file in files)
    lines = [
        "# WILQ Anti-Slop Complexity Audit",
        "",
        f"- Root: `{root}`",
        f"- Python files scanned: `{len(files)}`",
        f"- Python non-empty LOC: `{python_loc}`",
        f"- Changed files: `{len(changed)}`",
        f"- Frozen growth files changed: `{len(frozen_changed)}`",
        "",
        "## Frozen Growth Files",
    ]
    for path in sorted(FROZEN_GROWTH_FILES):
        status = "changed" if path in changed else "clean"
        lines.append(f"- `{path.as_posix()}`: {status}")

    if frozen_changed:
        lines.extend(["", "## Frozen Growth Risk"])
        lines.extend(f"- `{path.as_posix()}`" for path in frozen_changed)

    lines.extend(["", "## Largest Python Files"])
    lines.extend(render_file_rows(sorted(files, key=lambda item: item.loc, reverse=True), limit))

    lines.extend(["", "## Largest Python Functions"])
    lines.extend(
        render_block_rows(
            sorted(functions, key=lambda item: item.lines, reverse=True),
            limit,
        )
    )

    lines.extend(["", "## Highest Branch-Count Python Functions"])
    lines.extend(
        render_block_rows(
            sorted(functions, key=lambda item: item.branch_count, reverse=True),
            limit,
        )
    )

    lines.extend(["", "## Largest Python Classes"])
    lines.extend(
        render_block_rows(
            sorted(classes, key=lambda item: item.lines, reverse=True),
            limit,
        )
    )
    return "\n".join(lines) + "\n"


def render_file_rows(rows: list[FileMetric], limit: int) -> list[str]:
    if not rows:
        return ["- No Python files found."]
    return [f"- `{row.path.as_posix()}`: {row.loc} LOC" for row in rows[:limit]]


def render_block_rows(rows: list[CodeBlockMetric], limit: int) -> list[str]:
    if not rows:
        return ["- No Python blocks found."]
    return [
        (
            f"- `{row.path.as_posix()}:{row.line}` `{row.name}`: "
            f"{row.lines} lines, {row.branch_count} branches"
        )
        for row in rows[:limit]
    ]


if __name__ == "__main__":
    sys.exit(main())
