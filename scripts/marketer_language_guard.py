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
    Path("wilq/knowledge"),
    Path("wilq/opportunities"),
    Path("wilq/schemas"),
    Path("wilq/workflows"),
    Path(".agents/skills"),
)

ACTIVE_CONTRACT_FILES = (
    Path("docs/evals/cases/wilq-skill-eval-cases.json"),
    Path("scripts/codex_skill_eval.sh"),
    Path("scripts/verify.sh"),
    Path("tests/test_codex_skill_eval_cases.py"),
)

GOAL_005_WILKU_MATERIAL_FILES = (
    Path("scripts/record_goal_005_content_uat_result.py"),
    Path("scripts/goal_005_completion_check.py"),
    Path("docs/handoffs/2026-07-03-wilku-service-profile-review-now.md"),
    Path("docs/handoffs/2026-07-02-wilku-service-profile-start-card.md"),
    Path("docs/handoffs/2026-07-02-wilku-informal-positive-feedback.md"),
    Path("docs/handoffs/2026-07-01-wilku-content-uat-ready.md"),
)

ACTIVE_PLAN_FILES = (
    Path("PLAN.md"),
    Path("PLANS.md"),
    Path("docs/PROGRESS.md"),
    Path("docs/goals/001-goal.md"),
    Path("docs/CONTEXT.md"),
)

ACTIVE_GOAL_DIR = Path("docs/goals")
ONLY_ACTIVE_GOAL_FILE = Path("docs/goals/001-goal.md")

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
        "Use propozycja naprawy pliku produktowego.",
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
        "do sprawdzenia do sprawdzenia",
        "Avoid duplicated review wording after copy migrations.",
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
        "ID dowodu",
        "Use dowód w WILQ or dowody źródłowe in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "debugowaniu",
        "Use plain audit/sprawdzenie language instead of debug wording in marketer-facing UI.",
    ),
    ForbiddenPhrase(
        "Akcje do sprawdzenia negative keywords",
        "Use Polish Ads wording for exclusion review queues.",
    ),
    ForbiddenPhrase(
        "ActionObjecty",
        "Use akcje do sprawdzenia in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "Ads Doctor",
        "Use Google Ads or WILQ Google Ads in marketer-facing skill labels.",
    ),
    ForbiddenPhrase(
        "Daily Command",
        "Use Centrum pracy in marketer-facing skill labels.",
    ),
    ForbiddenPhrase(
        "Content Strategist",
        "Use Strategia treści in marketer-facing skill labels.",
    ),
    ForbiddenPhrase(
        "Campaign Builder",
        "Use Plan kampanii in marketer-facing skill labels.",
    ),
    ForbiddenPhrase(
        "Gap Finder",
        "Use Luki z Ahrefs in marketer-facing skill labels.",
    ),
    ForbiddenPhrase(
        "Social Publisher",
        "Use Posty społecznościowe in marketer-facing skill labels.",
    ),
    ForbiddenPhrase(
        "Feed Operator",
        "Use Merchant Center or plik produktowy language in marketer-facing skill labels.",
    ),
    ForbiddenPhrase(
        "status: " + "brak",
        "Use an API/domain label that explains the status is unconfirmed.",
    ),
    ForbiddenPhrase(
        "kanał: " + "brak",
        "Use an API/domain label that explains the campaign/channel type is unconfirmed.",
    ),
    ForbiddenPhrase(
        "GA4 Analyst",
        "Use Analityka GA4 in marketer-facing skill labels.",
    ),
    ForbiddenPhrase(
        "Content Doctor",
        "Use Treści z GSC in marketer-facing skill labels.",
    ),
    ForbiddenPhrase(
        "Skill Contract",
        "Use Kontrakt skilla in active skill docs.",
    ),
    ForbiddenPhrase(
        "Trigger Contract",
        "Use Kiedy używać in active skill docs.",
    ),
    ForbiddenPhrase(
        "evidence IDs",
        "Use identyfikatory dowodów in operator-facing skill prompts.",
    ),
    ForbiddenPhrase(
        "blockerów",
        "Use blokad in operator-facing skill prompts.",
    ),
    ForbiddenPhrase(
        "feed issues",
        "Use problemy pliku produktowego in Merchant copy.",
    ),
    ForbiddenPhrase(
        "feedu",
        "Use pliku produktowego in Merchant/product-file copy.",
    ),
    ForbiddenPhrase(
        "feedzie",
        "Use pliku produktowym in Merchant/product-file copy.",
    ),
    ForbiddenPhrase(
        "feedem",
        "Use plikiem produktowym in Merchant/product-file copy.",
    ),
    ForbiddenPhrase(
        "feed triage",
        "Use kolejka oceny pliku produktowego.",
    ),
    ForbiddenPhrase(
        "Merchant/feed",
        "Use Merchant i plik produktowy.",
    ),
    ForbiddenPhrase(
        "primary feed",
        "Use główny plik produktowy.",
    ),
    ForbiddenPhrase(
        "supplemental feed",
        "Use uzupełnienie pliku produktowego.",
    ),
    ForbiddenPhrase(
        "aggregate product/feed",
        "Use zagregowane fakty produktów i pliku produktowego.",
    ),
    ForbiddenPhrase(
        "query/page",
        "Use zapytania i adresy in content copy.",
    ),
    ForbiddenPhrase(
        "Zapytania/URL",
        "Use Zapytania i adresy z GSC in content copy.",
    ),
    ForbiddenPhrase(
        "zapytania/URL",
        "Use zapytania i adresy z GSC in content copy.",
    ),
    ForbiddenPhrase(
        "produkty=",
        "Use natural Polish metric phrases in operator summaries, not key=value report copy.",
    ),
    ForbiddenPhrase(
        "zgłoszenia=",
        "Use natural Polish metric phrases in operator summaries, not key=value report copy.",
    ),
    ForbiddenPhrase(
        "kampanie=",
        "Use natural Polish metric phrases in operator summaries, not key=value report copy.",
    ),
    ForbiddenPhrase(
        "koszt=",
        "Use natural Polish metric phrases in operator summaries, not key=value report copy.",
    ),
    ForbiddenPhrase(
        "luki treści=",
        "Use natural Polish metric phrases in operator summaries, not key=value report copy.",
    ),
    ForbiddenPhrase(
        "Pilne=",
        "Use natural Polish priority phrases in operator summaries, not key=value report copy.",
    ),
    ForbiddenPhrase(
        "wysokie=",
        "Use natural Polish priority phrases in operator summaries, not key=value report copy.",
    ),
    ForbiddenPhrase(
        "GSC↔WP",
        "Use Treści znalezione w WordPress or explicit GSC/WordPress wording.",
    ),
    ForbiddenPhrase(
        "Ahrefs↔WP",
        "Use Luki Ahrefs powiązane z WordPress.",
    ),
    ForbiddenPhrase(
        "GSC overlap",
        "Use Powiązanie z GSC.",
    ),
    ForbiddenPhrase(
        "WP overlap",
        "Use Powiązanie z WordPress.",
    ),
    ForbiddenPhrase(
        "GSC/WordPress",
        "Use GSC i WordPress without slash shorthand.",
    ),
    ForbiddenPhrase(
        "WordPress/GSC",
        "Use WordPress, GSC i Ahrefs without slash shorthand.",
    ),
    ForbiddenPhrase(
        "Status GA4 / pomiar i jakość ruchu",
        "Use a natural Polish status heading without slash shorthand.",
    ),
    ForbiddenPhrase(
        "Status Localo / widoczność lokalna",
        "Use a natural Polish status heading without slash shorthand.",
    ),
    ForbiddenPhrase(
        "Status Ahrefs / dowody SEO",
        "Use a natural Polish status heading without slash shorthand.",
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
        "akcje sprawdzone w WILQ",
        "Distinguish system control from human review: use akcje do sprawdzenia w WILQ.",
    ),
    ForbiddenPhrase(
        "akcji sprawdzonej w WILQ",
        "Distinguish system control from human review: use akcji do sprawdzenia w WILQ.",
    ),
    ForbiddenPhrase(
        "akcji sprawdzonych w WILQ",
        "Distinguish system control from human review: use akcji do sprawdzenia w WILQ.",
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
        "Brief treści do sprawdzenia",
        "Use Plan treści do sprawdzenia in marketer-facing content action detail.",
    ),
    ForbiddenPhrase(
        "Cel briefu",
        "Use Cel planu treści in marketer-facing content action detail.",
    ),
    ForbiddenPhrase(
        "podgląd briefu",
        "Use plan treści / podgląd planu treści in marketer-facing content copy.",
    ),
    ForbiddenPhrase(
        "podgląd briefu treści",
        "Use plan treści / podgląd planu treści in marketer-facing content copy.",
    ),
    ForbiddenPhrase(
        "mapowanie konwersji",
        "Use powiązanie konwersji in marketer-facing GA4 copy.",
    ),
    ForbiddenPhrase(
        "mapowanie strony wejścia",
        "Use sprawdzenie strony wejścia in marketer-facing GA4 copy.",
    ),
    ForbiddenPhrase(
        "mapowanie produktu Ads",
        "Use powiązanie produktu z Ads in marketer-facing Merchant copy.",
    ),
    ForbiddenPhrase(
        "zmapowane produkty",
        "Use powiązane produkty in marketer-facing Merchant copy.",
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
        "dowody techniczne",
        "Use dowody w WILQ or źródła danych; technical evidence wording is not marketer-first.",
    ),
    ForbiddenPhrase(
        "techniczne warunki akcji",
        "Use warunki zapisu akcji or warunki sprawdzenia.",
    ),
    ForbiddenPhrase(
        "techniczne potwierdzenie",
        "Use potwierdzenie dostępu or potwierdzenie odczytu.",
    ),
    ForbiddenPhrase(
        "skrót technicznych",
        "Use skrót źródeł danych / skrót blokad.",
    ),
    ForbiddenPhrase(
        "Szczegóły techniczne zostają niżej",
        "Use pełne warunki i dowody; technical detail belongs behind explicit drawers.",
    ),
    ForbiddenPhrase(
        "przykłady dostępne w szczegółach technicznych",
        "Use examples available in the full review.",
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
        "metric facts",
        "Use fakty z danych / metryki źródłowe in marketer-facing labels.",
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
        "social drafts",
        "Use szkice postów social / materiały social do sprawdzenia.",
    ),
    ForbiddenPhrase(
        "candidate inputs",
        "Use source_inputs / materiały źródłowe for social draft source signals.",
    ),
    ForbiddenPhrase(
        "candidate_inputs",
        "Use source_inputs for social draft source signals; do not keep stale candidate fields.",
    ),
    ForbiddenPhrase(
        "Szczegóły źródłowe",
        "Use condensed source context instead of exposing counts of technical fields.",
    ),
    ForbiddenPhrase(
        "post published",
        "Use opublikowanie posta / opublikowany post in social blocked claims.",
    ),
    ForbiddenPhrase(
        "social performance uplift",
        "Use wzrost skuteczności social in social blocked claims.",
    ),
    ForbiddenPhrase(
        "uplift",
        "Use plain Polish outcome wording such as wzrost, "
        "and only claim it when evidence allows it.",
    ),
    ForbiddenPhrase(
        "Demand Gen launch recommendation",
        "Use rekomendacja uruchomienia Demand Gen in Demand Gen blocked claims.",
    ),
    ForbiddenPhrase(
        "Demand Gen transition ready",
        "Use gotowość przejścia na Demand Gen in Demand Gen blocked claims.",
    ),
    ForbiddenPhrase(
        "creative quality verdict",
        "Use ocena jakości kreacji in Demand Gen blocked claims.",
    ),
    ForbiddenPhrase(
        "asset performance verdict",
        "Use ocena skuteczności assetów in Demand Gen blocked claims.",
    ),
    ForbiddenPhrase(
        "audience size",
        "Use rozmiar odbiorców in custom-segments and Keyword Planner blocked claims.",
    ),
    ForbiddenPhrase(
        "targeting applied",
        "Use zapis kierowania reklam in custom-segments blocked claims.",
    ),
    ForbiddenPhrase(
        "conversion uplift",
        "Use wzrost konwersji in custom-segments and Keyword Planner blocked claims.",
    ),
    ForbiddenPhrase(
        "campaign performance",
        "Use skuteczność kampanii in custom-segments and Keyword Planner blocked claims.",
    ),
    ForbiddenPhrase(
        "local task completed",
        "Use ukończone zadanie lokalne in Localo blocked claims.",
    ),
    ForbiddenPhrase(
        "GBP write",
        "Use zapis zmian w profilu firmy in Localo blocked claims.",
    ),
    ForbiddenPhrase(
        "GBP performance",
        "Use wyniki profilu firmy w Google in Localo blocked claims.",
    ),
    ForbiddenPhrase(
        "competitor visibility",
        "Use widoczność konkurencji in Localo blocked claims.",
    ),
    ForbiddenPhrase(
        "local visibility uplift",
        "Use poprawa widoczności lokalnej in Localo blocked claims.",
    ),
    ForbiddenPhrase(
        "write path",
        "Use zapis zmian in Localo/domain-facing copy.",
    ),
    ForbiddenPhrase(
        "lead uplift",
        "Use wzrost liczby leadów in content blocked claims.",
    ),
    ForbiddenPhrase(
        "revenue impact",
        "Use wpływ na przychód in content blocked claims.",
    ),
    ForbiddenPhrase(
        "ranking guarantee",
        "Use gwarancja pozycji in content blocked claims.",
    ),
    ForbiddenPhrase(
        "traffic uplift",
        "Use wzrost ruchu in Ahrefs/content blocked claims.",
    ),
    ForbiddenPhrase(
        "authority improvement",
        "Use wzrost autorytetu in Ahrefs/content blocked claims.",
    ),
    ForbiddenPhrase(
        "duplicate-free guarantee",
        "Use gwarancja braku duplikatów in content blocked claims.",
    ),
    ForbiddenPhrase(
        "automatic WordPress publish",
        "Use automatyczna publikacja WordPress in content blocked claims.",
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
        "key event",
        "Use zdarzenie kluczowe in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "landing page",
        "Use strona wejścia in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "landing pages",
        "Use strony wejścia in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "landingów",
        "Use stron wejścia in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "source/medium",
        "Use źródło i medium ruchu in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "source / medium",
        "Use źródło i medium ruchu in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "message match",
        "Use dopasowanie komunikatu in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "impact metrics",
        "Use metryki wpływu in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "match type",
        "Use typ dopasowania in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "N-gram:",
        "Use Temat in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "Canonical:",
        "Use Kontrola URL-a kanonicznego in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "Engagement rate",
        "Use współczynnik zaangażowania in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "Target ROAS",
        "Use docelowy zwrot z reklam in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "target ROAS",
        "Use docelowy zwrot z reklam in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "Target CPA",
        "Use docelowy koszt pozyskania celu in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "target CPA",
        "Use docelowy koszt pozyskania celu in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "wzrost performance",
        "Use wzrost skuteczności in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "werdykt performance",
        "Use werdykt skuteczności in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "product ROAS",
        "Use zwrot z reklam na poziomie produktu in marketer-facing Merchant copy.",
    ),
    ForbiddenPhrase(
        "product revenue recovery",
        "Use odzyskany przychód produktu in marketer-facing Merchant copy.",
    ),
    ForbiddenPhrase(
        "product fix impact",
        "Use efekt naprawy produktu in marketer-facing Merchant copy.",
    ),
    ForbiddenPhrase(
        "price change impact",
        "Use wpływ zmiany ceny in marketer-facing Merchant copy.",
    ),
    ForbiddenPhrase(
        "product profitability",
        "Use opłacalność produktu in marketer-facing Merchant copy.",
    ),
    ForbiddenPhrase(
        "performance metrics",
        "Use metryki skuteczności in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "performance rows",
        "Use wiersze skuteczności in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "before/after",
        "Use sprzed i po zmianie in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "claimować",
        "Use obiecywać / twierdzić in marketer-facing copy.",
    ),
    ForbiddenPhrase(
        "claimujemy",
        "Use obiecujemy / twierdzimy in marketer-facing copy.",
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

FORBIDDEN_PLAN_RULE_PHRASES = (
    "No recommendation without",
    "No write/apply without",
    "No evidence ID",
    "No source connector",
    "No preflight verdict",
    "No sales brief",
    "No claim review",
    "No audit",
    "No measurement window",
    "must not invent metrics",
)

GOAL_005_WILKU_FORBIDDEN_PHRASES = (
    ForbiddenPhrase(
        "eval:",
        "Use bramka: in Goal 005 Wilku-facing source trace output.",
    ),
    ForbiddenPhrase(
        "raw private text",
        "Use surowy prywatny tekst / surowego prywatnego tekstu.",
    ),
    ForbiddenPhrase(
        "completion proof",
        "Use Polish completion/evidence wording in Wilku-facing materials.",
    ),
    ForbiddenPhrase(
        "finalny content",
        "Use finalne treści.",
    ),
    ForbiddenPhrase(
        "Decyzja contentowa",
        "Use Decyzja treściowa WILQ.",
    ),
    ForbiddenPhrase(
        "kolejki content",
        "Use kolejki treści.",
    ),
    ForbiddenPhrase(
        "kolejka content",
        "Use kolejka treści.",
    ),
    ForbiddenPhrase(
        "trace czytelny",
        "Use ślad czytelny.",
    ),
)


def main() -> None:
    errors: list[str] = []
    errors.extend(_active_goal_file_errors())
    errors.extend(_active_plan_rule_errors())
    errors.extend(_goal_005_wilku_material_errors())
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


def _active_goal_file_errors() -> list[str]:
    if not ACTIVE_GOAL_DIR.exists():
        return []
    errors: list[str] = []
    for path in sorted(ACTIVE_GOAL_DIR.glob("*.md")):
        if path == ONLY_ACTIVE_GOAL_FILE:
            continue
        errors.append(
            f"{path.as_posix()}: archived or future goals must live under "
            "docs/goals/archive/. docs/goals/001-goal.md is the only active goal file."
        )
    return errors


def _active_plan_rule_errors() -> list[str]:
    errors: list[str] = []
    for path in ACTIVE_PLAN_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for phrase in FORBIDDEN_PLAN_RULE_PHRASES:
            if phrase not in text:
                continue
            for line_number, line in _matching_lines(text, phrase):
                errors.append(
                    f"{path.as_posix()}:{line_number}: old English rule wording "
                    f"{phrase!r} is forbidden in active plan/recovery docs. "
                    f"Use Polish WILQ operating language. Line: {line.strip()}"
                )
    return errors


def _goal_005_wilku_material_errors() -> list[str]:
    errors: list[str] = []
    for path in GOAL_005_WILKU_MATERIAL_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for forbidden in GOAL_005_WILKU_FORBIDDEN_PHRASES:
            if forbidden.phrase not in text:
                continue
            for line_number, line in _matching_lines(text, forbidden.phrase):
                errors.append(
                    f"{path.as_posix()}:{line_number}: forbidden Goal 005 Wilku-facing "
                    f"phrase {forbidden.phrase!r}. {forbidden.reason} "
                    f"Line: {line.strip()}"
                )
    return errors


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
