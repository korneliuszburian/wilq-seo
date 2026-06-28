from __future__ import annotations

import re
from pathlib import Path

SKILL_ROOT = Path(".agents/skills")
EXPECTED_SKILLS = {
    "wilq-daily-command",
    "wilq-ads-doctor",
    "wilq-gsc-content-doctor",
    "wilq-ahrefs-gap-finder",
    "wilq-localo-operator",
    "wilq-content-strategist",
    "wilq-social-publisher",
    "wilq-campaign-builder",
    "wilq-custom-segments",
    "wilq-demand-gen-operator",
    "wilq-ga4-analyst",
    "wilq-merchant-feed-operator",
}
FORBIDDEN_SKILL_PROSE = {
    "Goal 001",
    "GOAL 001",
    "goal 001",
    "workaround",
    "bugfix",
    "outdated",
    "temporary",
    "hack",
    "slop",
    "Product inspiration:",
    "Inspiracja produktowa",
    "MCP Boundary",
    "Content Safety",
    "Merchant Safety",
    "GA4 Safety",
    "Then fetch",
    "Do not rebuild",
    "with mode=vendor_read",
    "API identifiers",
    "Priorytetyzuj Merchant",
    "Klasyfikuj każdy item",
    "WILQ nie ma Localo ranking/GBP evidence",
    "Localo nie zostało wypromowane",
    "docs/goals/",
    "docs/PROGRESS",
    "docs/evals/",
    ".local-lab/",
    "previous run",
    "last run",
    "ostatni przebieg",
    "poprzedni przebieg",
    "prompt-fix",
    "prompt fix",
    "napraw skill",
    "naprawa skilla",
    "blockery",
    "znane blockery",
    "blocker report",
    "zwróć blocker",
    "Pokaż blocker",
    "daily command center",
    "Command Center",
    "Content Planner",
    "Ads Doctor",
}
ENGLISH_WORKFLOW_PREFIX = re.compile(r"^\d+\.\s+(Call|Run|Use|Check|Fix|Build)\b")
MAX_BODY_LINE_LENGTH = 900
DEDICATED_DIAGNOSTICS_ENDPOINTS = {
    "wilq-ads-doctor": "/api/ads/diagnostics",
    "wilq-ahrefs-gap-finder": "/api/ahrefs/diagnostics",
    "wilq-content-strategist": "/api/content/diagnostics",
    "wilq-custom-segments": "/api/ads/diagnostics",
    "wilq-demand-gen-operator": "/api/demand-gen/diagnostics",
    "wilq-ga4-analyst": "/api/ga4/diagnostics",
    "wilq-gsc-content-doctor": "/api/content/diagnostics",
    "wilq-localo-operator": "/api/localo/diagnostics",
    "wilq-merchant-feed-operator": "/api/merchant/diagnostics",
}


def main() -> None:
    errors: list[str] = []
    missing = sorted(
        name for name in EXPECTED_SKILLS if not (SKILL_ROOT / name / "SKILL.md").exists()
    )
    if missing:
        errors.append(f"Missing skill folders: {missing}")

    for skill_name in sorted(EXPECTED_SKILLS):
        skill_dir = SKILL_ROOT / skill_name
        if not skill_dir.exists():
            continue
        errors.extend(_skill_errors(skill_name, skill_dir))

    if errors:
        raise SystemExit("Skill hygiene check failed:\n- " + "\n- ".join(errors))
    print("Skill hygiene check passed")


def _skill_errors(skill_name: str, skill_dir: Path) -> list[str]:
    errors: list[str] = []
    markdown_files = sorted([skill_dir / "SKILL.md", *skill_dir.glob("references/*.md")])
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        relative = path.as_posix()
        for phrase in FORBIDDEN_SKILL_PROSE:
            if phrase in text:
                errors.append(f"{relative}: forbidden prose {phrase!r}")
        if path.name == "SKILL.md":
            errors.extend(_skill_md_errors(skill_name, path, text))
        if path.name == "output-contract.md":
            errors.extend(_output_contract_errors(skill_name, path, text))
        errors.extend(_long_line_errors(path, text))
    return errors


def _skill_md_errors(skill_name: str, path: Path, text: str) -> list[str]:
    errors: list[str] = []
    relative = path.as_posix()
    if f"name: {skill_name}" not in text:
        errors.append(f"{relative}: frontmatter name must be {skill_name!r}")
    if "Polish language contract" not in text:
        errors.append(f"{relative}: missing Polish language contract guardrail")
    for line_number, line in enumerate(text.splitlines(), start=1):
        if ENGLISH_WORKFLOW_PREFIX.match(line):
            errors.append(
                f"{relative}:{line_number}: workflow step starts with English imperative"
            )
    errors.extend(_diagnostics_first_errors(skill_name, path, text))
    return errors


def _output_contract_errors(skill_name: str, path: Path, text: str) -> list[str]:
    return _diagnostics_first_errors(skill_name, path, text)


def _diagnostics_first_errors(skill_name: str, path: Path, text: str) -> list[str]:
    endpoint = DEDICATED_DIAGNOSTICS_ENDPOINTS.get(skill_name)
    if endpoint is None:
        return []
    diagnostics_call = f"GET {endpoint}"
    context_pack_call = "POST /api/codex/context-pack"
    diagnostics_index = text.find(diagnostics_call)
    context_pack_index = text.find(context_pack_call)
    if diagnostics_index == -1:
        return [f"{path.as_posix()}: missing diagnostics-first endpoint {endpoint!r}"]
    if context_pack_index != -1 and diagnostics_index > context_pack_index:
        return [
            f"{path.as_posix()}: diagnostics endpoint must be documented before context-pack"
        ]
    return []


def _long_line_errors(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    in_frontmatter = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line_number == 1 and line == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and line == "---":
            in_frontmatter = False
            continue
        if in_frontmatter:
            continue
        if len(line) > MAX_BODY_LINE_LENGTH:
            errors.append(
                f"{path.as_posix()}:{line_number}: line exceeds "
                f"{MAX_BODY_LINE_LENGTH} characters"
            )
    return errors


if __name__ == "__main__":
    main()
