from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ForbiddenPhrase:
    phrase: str
    reason: str


ACTIVE_SOURCE_ROOTS = (
    Path("apps/dashboard/src/components"),
    Path("apps/dashboard/src/lib"),
    Path("apps/dashboard/src/routes"),
    Path("wilq/actions"),
    Path("wilq/briefing"),
    Path("wilq/schemas.py"),
    Path(".agents/skills"),
)

ACTIVE_CONTRACT_FILES = (
    Path("docs/evals/cases/wilq-skill-eval-cases.json"),
    Path("scripts/codex_skill_eval.sh"),
    Path("scripts/verify.sh"),
    Path("tests/test_codex_skill_eval_cases.py"),
)

SKIP_SUFFIXES = (
    ".test.ts",
    ".test.tsx",
    ".spec.ts",
    ".spec.tsx",
    ".pyc",
)

SKIP_PARTS = {
    "__pycache__",
    "scripts",
}

FORBIDDEN_PHRASES = (
    ForbiddenPhrase(
        "kandydat zmiany",
        "Use marketer-facing action language: akcja do sprawdzenia / propozycja.",
    ),
    ForbiddenPhrase(
        "kandydat",
        "Use propozycja or akcja do sprawdzenia in marketer-facing contracts.",
    ),
    ForbiddenPhrase(
        "kandydata",
        "Use propozycja or akcja do sprawdzenia in marketer-facing contracts.",
    ),
    ForbiddenPhrase(
        "kandydaci",
        "Use propozycje or akcje do sprawdzenia in marketer-facing contracts.",
    ),
    ForbiddenPhrase(
        "kandydatów",
        "Use propozycje or akcje do sprawdzenia in marketer-facing contracts.",
    ),
    ForbiddenPhrase(
        "kandydatem",
        "Use propozycją or akcją do sprawdzenia in marketer-facing contracts.",
    ),
    ForbiddenPhrase(
        "kandydat naprawy feedu",
        "Use propozycja naprawy feedu.",
    ),
    ForbiddenPhrase(
        "kandydat contentowy",
        "Use propozycja treści.",
    ),
    ForbiddenPhrase(
        "kandydatów custom segments",
        "Use propozycje custom segments.",
    ),
    ForbiddenPhrase(
        "Kandydat:",
        "Do not expose candidate IDs as primary marketer copy.",
    ),
    ForbiddenPhrase(
        "Dry-run",
        "Use podgląd zmian / sprawdzenie w WILQ.",
    ),
    ForbiddenPhrase(
        "dry-run",
        "Use podgląd zmian / sprawdzenie w WILQ.",
    ),
    ForbiddenPhrase(
        " / draft",
        "Translate WordPress post status to szkic before showing it to the marketer.",
    ),
    ForbiddenPhrase(
        "Status pozostaje `draft`",
        "Use plain Polish status wording instead of raw WordPress status values.",
    ),
    ForbiddenPhrase(
        "Szkic stagingowy",
        "Use WordPress draft / przekazanie language; staging is not the marketer-facing model.",
    ),
    ForbiddenPhrase(
        "Staging:",
        "Use Przekazanie / podgląd language; staging is not the marketer-facing model.",
    ),
    ForbiddenPhrase(
        "Local Visibility Focus",
        "Use plain Polish route section headings.",
    ),
    ForbiddenPhrase(
        "Social Publishing Focus",
        "Use plain Polish route section headings.",
    ),
    ForbiddenPhrase(
        "Content Growth Focus",
        "Use plain Polish route section headings.",
    ),
    ForbiddenPhrase(
        "Feed/Product Focus",
        "Use plain Polish route section headings.",
    ),
    ForbiddenPhrase(
        "Safety Gate",
        "Use Brama bezpieczeństwa in marketer-facing headings.",
    ),
    ForbiddenPhrase(
        "Evidence Registry",
        "Do not expose registry fallback headings in marketer-facing surfaces.",
    ),
    ForbiddenPhrase(
        "Connector Refresh Runs",
        "Do not expose connector refresh registry headings in marketer-facing surfaces.",
    ),
    ForbiddenPhrase(
        "Connector Status",
        "Use Dostęp do źródeł danych / stan dostępu.",
    ),
    ForbiddenPhrase(
        "API-backed operating surface",
        "Use plain Polish route descriptions.",
    ),
    ForbiddenPhrase(
        "tylko do sprawdzenia",
        "Use do sprawdzenia / do kontroli without artifact language.",
    ),
    ForbiddenPhrase(
        "wykonanie zmian",
        "Use zapis zmian when describing allowed writes.",
    ),
    ForbiddenPhrase(
        "wykonanie rekomendacji",
        "Use zapis zmian rekomendacji.",
    ),
    ForbiddenPhrase(
        "gdy walidacja przejdzie",
        "Use gdy sprawdzenie w WILQ przejdzie.",
    ),
    ForbiddenPhrase(
        "walidacja przejdzie",
        "Use sprawdzenie w WILQ przejdzie.",
    ),
    ForbiddenPhrase(
        "ActionObject IDs",
        "Use action IDs only in technical contracts; do not promote ActionObject wording.",
    ),
    ForbiddenPhrase(
        "ActionObjecty",
        "Use akcje do sprawdzenia in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "akcja WILQ",
        "Use akcja do sprawdzenia or sprawdzenie w WILQ.",
    ),
    ForbiddenPhrase(
        "akcję WILQ",
        "Use akcję do sprawdzenia or sprawdzenie w WILQ.",
    ),
    ForbiddenPhrase(
        "akcji WILQ",
        "Use akcji do sprawdzenia or sprawdzenie w WILQ.",
    ),
    ForbiddenPhrase(
        "akcje WILQ",
        "Use akcje do sprawdzenia or sprawdzenie w WILQ.",
    ),
    ForbiddenPhrase(
        "akcja w WILQ",
        "Use propozycja w WILQ or akcja do sprawdzenia.",
    ),
    ForbiddenPhrase(
        "akcję w WILQ",
        "Use propozycję w WILQ or akcję do sprawdzenia.",
    ),
    ForbiddenPhrase(
        "akcji w WILQ",
        "Use propozycji w WILQ or akcji do sprawdzenia.",
    ),
    ForbiddenPhrase(
        "akcje w WILQ",
        "Use propozycje w WILQ or akcje do sprawdzenia.",
    ),
    ForbiddenPhrase(
        "akcjach WILQ",
        "Use akcjach do sprawdzenia.",
    ),
    ForbiddenPhrase(
        "akcjach w WILQ",
        "Use propozycjach w WILQ or akcjach do sprawdzenia.",
    ),
    ForbiddenPhrase(
        "migration-map",
        "Dev preview and migration-map language is obsolete for Ekologus content.",
    ),
    ForbiddenPhrase(
        "mapping-review",
        "Use public/final URL review language instead of mapping-review.",
    ),
    ForbiddenPhrase(
        "mapping_review",
        "Use public/final URL review language instead of mapping_review.",
    ),
    ForbiddenPhrase(
        "target_site",
        "Use source_public_url, final_canonical_url, intended_final_url or preview_url.",
    ),
    ForbiddenPhrase(
        "target site",
        "Use public/final URL or optional preview context language.",
    ),
    ForbiddenPhrase(
        "API/evidence",
        "Use dane źródłowe / dowody w WILQ in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "Dowody w API",
        "Use Dowody w WILQ.",
    ),
    ForbiddenPhrase(
        "Blockery",
        "Use Blokady in marketer-facing labels and fixtures.",
    ),
    ForbiddenPhrase(
        "Metric facts",
        "Use Fakty z danych / metryki źródłowe in marketer-facing labels.",
    ),
    ForbiddenPhrase(
        "GSC clicks",
        "Use kliknięcia z GSC.",
    ),
    ForbiddenPhrase(
        "content opportunities",
        "Use okazje contentowe / kolejka treści.",
    ),
    ForbiddenPhrase(
        "post candidates",
        "Use propozycje postów.",
    ),
    ForbiddenPhrase(
        "LinkedIn credentials",
        "Use dostęp LinkedIn.",
    ),
    ForbiddenPhrase(
        "gotowość adaptera",
        "Use gotowość dostępu or stan odczytu danych.",
    ),
    ForbiddenPhrase(
        "jako adapterem",
        "Use odczytywać dane from the source instead of adapter wording.",
    ),
    ForbiddenPhrase(
        "lista connectorów",
        "Use lista źródeł danych.",
    ),
    ForbiddenPhrase(
        "brakujące credentiale",
        "Use braki dostępu.",
    ),
    ForbiddenPhrase(
        "credential names",
        "Use braki dostępu or liczba brakujących pól dostępu.",
    ),
    ForbiddenPhrase(
        "gotowość connectora",
        "Use dostęp do źródła danych.",
    ),
    ForbiddenPhrase(
        "awarię connectora",
        "Use awarię źródła danych.",
    ),
    ForbiddenPhrase(
        "sales brief",
        "Use brief or brief sprzedażowy in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "claim review",
        "Use sprawdzenie ryzykownych obietnic.",
    ),
    ForbiddenPhrase(
        "claimy",
        "Use twierdzenia, obietnice or ryzykowne obietnice in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "claimów",
        "Use twierdzeń, obietnic or ryzykownych obietnic in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "Blokady claimów",
        "Use Nie wolno twierdzić / Nie wolno obiecać.",
    ),
    ForbiddenPhrase(
        "Zablokowane claimy",
        "Use Nie wolno twierdzić / Nie wolno obiecać.",
    ),
    ForbiddenPhrase(
        "revenue albo lead uplift",
        "Use plain Polish: przychód / wzrost leadów, and only as blocked claims.",
    ),
    ForbiddenPhrase(
        "revenue/lead uplift",
        "Use plain Polish: przychód / wzrost leadów, and only as blocked claims.",
    ),
    ForbiddenPhrase(
        "Overlap:",
        "Use Wspólne sygnały or Wspólne zapytania.",
    ),
)


def main() -> None:
    errors: list[str] = []
    for path in _iter_active_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for forbidden in FORBIDDEN_PHRASES:
            if forbidden.phrase not in text:
                continue
            for line_number, line in _matching_lines(text, forbidden.phrase):
                errors.append(
                    f"{path.as_posix()}:{line_number}: forbidden marketer phrase "
                    f"{forbidden.phrase!r}. {forbidden.reason} Line: {line.strip()}"
                )
    if errors:
        raise SystemExit("Marketer language guard failed:\n- " + "\n- ".join(errors))
    print("Marketer language guard passed")


def _iter_active_files() -> list[Path]:
    files: list[Path] = []
    for root in ACTIVE_SOURCE_ROOTS:
        if not root.exists():
            continue
        if root.is_file():
            if _is_supported_file(root):
                files.append(root)
            continue
        for path in root.rglob("*"):
            if _is_supported_file(path):
                files.append(path)
    for path in ACTIVE_CONTRACT_FILES:
        if path.exists() and path.is_file():
            files.append(path)
    return sorted(files)


def _is_supported_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if any(part in SKIP_PARTS for part in path.parts):
        return False
    if any(path.name.endswith(suffix) for suffix in SKIP_SUFFIXES):
        return False
    return path.suffix in {".py", ".ts", ".tsx", ".md", ".yaml", ".yml"}


def _matching_lines(text: str, phrase: str) -> list[tuple[int, str]]:
    return [
        (line_number, line)
        for line_number, line in enumerate(text.splitlines(), start=1)
        if phrase in line
    ]


if __name__ == "__main__":
    main()
