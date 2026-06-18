# WILQ Context Index

Ten plik jest indeksem recovery po utracie kontekstu. Nie zastępuje goalu ani
AGENTS.md; wskazuje, gdzie leży aktualna prawda operacyjna.

## Start Here

1. `AGENTS.md` - stałe reguły pracy, sekrety, lokalne ścieżki i gotchas.
2. `docs/goals/001-goal.md` - jedyny aktywny goal i kolejka następnych zadań.
3. `docs/PROGRESS.md` - najnowszy stan slice'ów, testów i decyzji.
4. `docs/evals/skill-eval-ledger.md` - przebiegi ręcznych i non-interactive testów skillów.
5. `docs/research/wilq-marketing-source-map.md` - źródła marketingowe i techniczne.
6. `docs/architecture/bdos-class-wilq-operating-system.md` - poprzeczka produktowa.
7. `docs/architecture/codex-runtime.md` - Codex skills, hooks, evals i runtime.
8. `docs/audits/001-output.md` - świeży audyt 2026-06-18: co zatrzymać, co
   zacząć i pięć następnych slice'ów dla marketera.

## Current Critical Direction

Audit `docs/audits/001-output.md` is now folded into
`docs/goals/001-goal.md`. The current order is:

1. Command Center first-screen cleanup is implemented and verified: one
   `Dzisiejsze decyzje marketera` board, no duplicated `Plan działań marketera`
   and no full connector blocker cards on `/command-center`.
2. Ads campaign activity read contract is implemented. Continue with search
   terms, conversions, recommendations, change history, budget pacing and
   impression share before any money-leak/CPA/ROAS/search-term claims.
3. Repair each skill only after the matching API/read contract exists.

Recently completed and pushed foundations:

- `2e0b0dc feat(content): expose content decision queue`
- `39511ac feat(command-center): add daily decision model`
- `8cfdf83 perf(codex): scope daily command context pack`
- `de09cab perf(api): batch metric fact reads`

Current performance slice truth:

- `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` now defaults
  to `context_scope.mode=daily`.
- Default daily context excludes full tactical queue and diagnostics. Use
  `{"skill":"wilq-daily-command","full_context":true}` for debug/full mode.
- Latest fresh `:8011` proof after the local patch:
  - daily context-pack: about `2.9s`, `160053 bytes`;
  - full daily context-pack: about `6.5s`, `998704 bytes`;
  - marketing brief: about `0.5s`, `46072 bytes`;
  - command-center: about `2.1-2.4s`, `30521 bytes`.
- Current follow-up adds a shared `DailyRuntime` view-model for
  daily Codex context. It builds `command_center`, `marketing_brief` and core
  actions from one connector/action/refresh snapshot and caches that runtime
  for a short TTL. Fresh helper API proof on `:8011`: cold daily context
  `3.047s`, then warm cached daily context `0.467s`, `0.544s`, `0.470s`, same
  payload size `160478 bytes`.
- This is improved from the old full context-pack (`~996 KB`, `~15s`) but not
  done. Batch DuckDB reads and read-only metric-store connections fixed a
  conflicting-lock runtime risk. Remaining cold-run bottleneck: diagnostics
  inside Command Center, especially the tactical/diagnostic joins used before
  Merchant issue-level triage and URL normalization are fully shaped.

Current Merchant slice truth:

- `MerchantIssueCluster` is implemented in Python and shared frontend schemas.
- `/api/merchant/diagnostics` returns `issue_clusters` grouped by issue type,
  affected attribute, country, reporting context, severity and resolution.
- `act_review_merchant_feed_issues` includes issue clusters in its payload.
- Dashboard `/merchant` renders issue clusters as the primary review queue.
- Full `scripts/verify.sh` passed for this slice on 2026-06-18.
- Current Merchant read contract still exposes aggregate issue dimensions and
  counts only; no sample product IDs/titles yet.

Current content URL normalization truth:

- Tactical queue reads enough WordPress inventory rows from DuckDB to keep large
  sitemap inventories in the WordPress index.
- GSC full URLs and GA4 landing paths are normalized to stable path keys.
- `ContentDecisionItem` now exposes `normalized_page_path`,
  `wordpress_match_confidence` and `wordpress_content_url`.
- Context-pack redaction preserves these public URL/path fields while still
  redacting token-like secret values.
- Direct checkout proof shows BDO, Zielony Ład and remediacja GSC URLs as
  `found exact_url`; GA4 landing paths resolve with `path_fallback`.
- Full `scripts/verify.sh` passed for this slice on 2026-06-18.

Current Command Center cleanup truth:

- `/command-center` renders `daily_decisions` as the single marketer decision
  board.
- The old summary/plan duplication is removed from the first screen.
- Full connector blocker/status cards are no longer rendered on
  `/command-center`; the compact `Źródła i ograniczenia` footer links to
  `/settings`.
- Focused frontend/backend checks and full `scripts/verify.sh` passed on
  2026-06-18 after the cleanup.

Current Ads Doctor contract truth:

- `/api/ads/diagnostics.campaign_read_contract` is typed and rendered on
  `/ads-doctor`.
- It groups live Google Ads metric facts into campaign rows with campaign ID,
  campaign name, clicks, impressions, cost micros, evidence IDs and blocked
  claims.
- It explicitly limits allowed metrics to `clicks`, `impressions` and
  `cost_micros`.
- It explicitly lists missing read contracts: `search_term_view`,
  `conversions`, `conversion_value`, `recommendations`, `change_history`,
  `budget_pacing` and `impression_share`.
- Live local proof after restarting API on `:8000` showed 18 campaign rows.
- Do not claim CPA, ROAS, search terms, wasted budget, negative keyword
  candidates, budget scaling or conversion drops until those read contracts
  exist.

Do not repair product logic inside skill references. If a skill needs a better
decision, add the typed WILQ API/schema/view-model field first and make the
skill consume it.

## Current Runtime

- API: `http://127.0.0.1:8000`
- Dashboard: `http://127.0.0.1:5173/command-center`
- API health: `curl -sf http://127.0.0.1:8000/api/health`
- Final gate: `scripts/verify.sh`

## Skill Eval Harness

Istniejący harness non-interactive:

```bash
scripts/codex_skill_eval.sh --all --api-base http://127.0.0.1:8000
scripts/codex_skill_eval.sh --skill wilq-content-strategist --api-base http://127.0.0.1:8000
```

Ważne pliki:

- `scripts/codex_skill_eval.sh`
- `docs/evals/cases/wilq-skill-eval-cases.json`
- `docs/evals/schemas/wilq-skill-eval-result.schema.json`
- `.agents/skills/*/scripts/smoke_*`

Harness sprawdza schema, język PL, API usage, evidence/source connectors i
ActionObject safety. Nie zastępuje ręcznej oceny użyteczności odpowiedzi dla
marketera; tę ocenę zapisujemy w `docs/evals/skill-eval-ledger.md`.

## Skill Eval Pipeline

Cel: udowodnić, że WILQ skill realnie pomaga polskiemu marketerowi, a nie tylko
zwraca poprawny JSON. Każdy skill musi przejść przez ten sam pipeline.

### 1. Preflight

Sprawdź aktualną prawdę runtime:

```bash
curl -sf http://127.0.0.1:8000/api/health
git status --short
```

Nie zaczynaj od pamięci rozmowy. Jeśli API nie działa, najpierw napraw runtime
albo zapisz blocker w `docs/PROGRESS.md`.

### 2. Ręczny prompt marketera

Użyj realistycznego polskiego promptu, takiego jak marketer faktycznie zada:

```text
Użyj skilla wilq-content-strategist. Zbuduj kolejkę content refresh, merge,
create albo block dla Ekologus na podstawie GSC, WordPress, GA4 i Ahrefs
evidence. Nie obiecuj leadów, revenue ani wzrostów pozycji.
```

Oczekiwany przebieg:

- skill czyta swój `SKILL.md`,
- skill czyta wymagane `references/`,
- skill pobiera WILQ API evidence,
- skill cytuje source connector IDs i evidence IDs,
- skill wskazuje ActionObject IDs, jeśli API je udostępnia,
- skill blokuje unsupported claims,
- odpowiedź jest po polsku z polskimi znakami.

Manualny wynik zapisuj w `docs/evals/skill-eval-ledger.md`, nawet jeśli potem
non-interactive eval przejdzie. Manualny przebieg jest często bogatszy i pokazuje
realną użyteczność dla marketera.

### 3. Deterministic smoke

Uruchom smoke script skilla:

```bash
uv run python .agents/skills/<skill>/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
```

Dla `wilq-daily-command` użyj:

```bash
uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
```

Smoke potwierdza kontrakt API/skilla, ale sam nie dowodzi jakości odpowiedzi.

### 4. Non-interactive Codex eval

Uruchom `codex exec` przez harness:

```bash
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 \
  scripts/codex_skill_eval.sh --skill <skill> --api-base http://127.0.0.1:8000
```

Używaj `CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1`, gdy globalna konfiguracja
Codexa/MCP może powodować poboczne błędy transportu. Eval ma mierzyć WILQ
skill/API, nie przypadkowe globalne narzędzia.

Wyniki zapisują się w:

```text
.local-lab/evals/codex-skill/<timestamp>/<skill>/
  prompt.md
  result.json
  trace.jsonl
  stderr.log
```

Nie commituj `.local-lab`.

### 5. Interpretacja pass/fail

`passed` oznacza tylko, że wynik spełnił obecne warunki harnessa:

- `language=pl-PL`,
- polskie znaki,
- `api_used=true`,
- zgodność ze schemą,
- source connectors,
- evidence IDs,
- ActionObject safety,
- brak oczywistych unsafe claims.

To nie zawsze oznacza, że skill dał świetną decyzję marketingową. Po każdym
passie zapisz ocenę jakości:

- Czy odpowiedź jest konkretna, czy ogólna?
- Czy daje kolejkę decyzji, czy tylko opisuje zasady?
- Czy używa tych samych evidence IDs co dashboard/API?
- Czy wskazuje najmniejszy bezpieczny następny krok?
- Czy blokuje metryki, których WILQ nie ma?
- Czy marketer może od razu coś zrobić?

Jeśli pass jest zbyt ogólny, nie traktuj go jako koniec pracy. Dopisz gap do
`docs/evals/skill-eval-ledger.md` i wzmocnij case/harness tak, żeby wymagał
konkretnych decyzji.

### 6. Aktualizacja dokumentów

Po każdym istotnym przebiegu zaktualizuj:

- `docs/evals/skill-eval-ledger.md` - prompt, endpointy, wynik, evidence IDs,
  ActionObject IDs, jakość odpowiedzi i product gaps.
- `docs/PROGRESS.md` - krótki aktualny stan i ścieżka artefaktu.
- `docs/goals/001-goal.md` - tylko jeśli zmienia się aktywny goal, blocker,
  acceptance gate albo następny krok.

### Aktualny znany wynik referencyjny

Pierwszy pełny przebieg:

```text
skill: wilq-content-strategist
manual prompt: completed and useful
non-interactive eval: passed
artifact: .local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/result.json
```

Wynik zawierał:

- `pl-PL`,
- polskie znaki,
- `api_used=true`,
- evidence IDs,
- source connectors,
- `act_prepare_content_refresh_queue`.

Najważniejszy wniosek: obecny harness dobrze łapie kontrakt, API usage i brak
halucynacji, ale za słabo mierzy "czy skill dał świetną kolejkę decyzji".
Manualny przebieg był bogatszy, bo wyciągnął konkretne decyzje: BDO refresh,
Zielony Ład merge/create-after-inventory-check, homepage low-priority refresh i
GA4 `(not set)` jako block. Następny poziom evali musi tego wymagać wprost.

### Następna kolejność skillów

Najpierw testuj skille, które mają realne ActionObjects i największą wartość
dla demo:

1. `wilq-merchant-feed-operator` - `act_review_merchant_feed_issues`.
2. `wilq-ga4-analyst` - `act_review_ga4_tracking_quality`.
3. `wilq-gsc-content-doctor` - `act_prepare_content_refresh_queue`.
4. `wilq-ads-doctor` - live campaign evidence; search terms/CPA/ROAS nadal
   wymagają osobnych read contracts.
5. `wilq-localo-operator` - access działa, ale local ranking/GBP facts są nadal
   blocked.

Po nich wróć do skillów bez aktualnego ActionObject i oceń, czy powinny dostać
nowe API/action contracts, czy pozostać blocker/readiness workflows.

## Current Product Direction

Command Center ma być "co marketer robi dziś", nie connector inventory.
Codex skills mają być operacyjną warstwą nad WILQ API: najpierw API evidence,
potem diagnoza, blokady claimów i bezpieczny następny krok po polsku.

## Current Critical Direction - 2026-06-18 13:55

Najważniejszy świeży audyt:

```txt
docs/audits/001-output.md
```

Wniosek audytu: architektura idzie w dobrym kierunku, ale WILQ jest nadal
`safe operating shell`, nie pełny BDOS-class OS. Największy problem to nie
liczba skillów, tylko brak jednego canonical operator view modelu i brak części
read/action contracts. API ma być mózgiem; skills mają być cienkimi workflow po
API.

Twarda zasada zapisana w `AGENTS.md`: nie wolno łatać logiki produktu,
deduplikacji, klasyfikacji decyzji, rankingów ani edge-case fixes w skill
references. Jeśli skill potrzebuje mądrzejszej decyzji, najpierw implementujemy
typed WILQ API/schema/view-model, a skill tylko konsumuje pole API.

## Active Uncommitted Slice - Content Decision Queue

Aktualny worktree ma aktywny, niecommitowany slice. Nie zaczynaj od zera.

Cel slice'a:

- Przenieść content decision logic z promptów/skilli do WILQ API.
- Dodać typed `ContentDecisionItem` i `ContentDiagnosticsResponse.decision_queue`.
- `wilq-content-strategist` ma używać `content_diagnostics.decision_queue`, nie
  odtwarzać logiki w references.
- Context-pack redaction ma zachowywać enumy `decision_type` /
  `decision_types`, bo to trace IDs/enum values, nie sekrety.

Zmienione pliki w toku:

- `wilq/schemas.py`
- `wilq/briefing/content_diagnostics.py`
- `wilq/security/redaction.py`
- `tests/test_api_contracts.py`
- `.agents/skills/wilq-content-strategist/SKILL.md`
- `.agents/skills/wilq-content-strategist/references/output-contract.md`
- `.agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py`
- `docs/evals/cases/wilq-skill-eval-cases.json`
- `AGENTS.md`

Live proof po restarcie API:

```bash
uv run python .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
```

Wynik smoke:

- `decision_types`:
  - `block_as_tracking_not_content`
  - `inventory_check_before_create`
  - `inventory_check_before_create`
  - `merge_create_after_inventory_check`
  - `inventory_check_before_create`
- `decision_queue` pochodzi z `/api/content/diagnostics`, nie ze skill
  reference.
- GA4 `(not set)` / `tracking_gap` jest blokowane jako content task.
- Zielony Ład jest jednym klastrem
  `merge_create_after_inventory_check`, nie siedmioma osobnymi rekomendacjami.
- BDO i inne URL-e z `wordpress_match=missing` są
  `inventory_check_before_create`, nie gotowym create/refresh.

Focused checks, które już przeszły dla tego slice'a:

```bash
uv run ruff check wilq/briefing/content_diagnostics.py wilq/security/redaction.py wilq/schemas.py .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py
uv run mypy wilq/briefing/content_diagnostics.py wilq/security/redaction.py wilq/schemas.py .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py
uv run pytest tests/test_api_contracts.py -q -k 'redaction_preserves_env_names_but_redacts_token_values or content_diagnostics_exposes_query_page_inventory_queue or codex_context_pack_embeds_marketing_brief_contract'
uv run pytest tests/test_codex_skill_eval_cases.py -q
```

Non-interactive eval po poprawce:

```txt
.local-lab/evals/codex-skill/20260618T114810Z/wilq-content-strategist/result.json
```

Wynik evala:

- `language=pl-PL`
- `api_used=true`
- 11 evidence IDs
- `operator_usefulness_score=4`
- rekomendacje używają `content_diagnostics.decision_queue`
- zawiera `inventory_check_before_create`,
  `merge_create_after_inventory_check`, `block_as_tracking_not_content`
- `act_prepare_content_refresh_queue` pozostaje prepare-only i wymaga
  walidacji przed apply.

Następny krok po wznowieniu:

1. Uzupełnić `docs/PROGRESS.md`, `docs/evals/skill-eval-ledger.md` i
   `docs/goals/001-goal.md` o ten slice.
2. Uruchomić focused checks jeszcze raz.
3. Commit semantic, np.
   `feat(content): expose content decision queue`.
4. Potem wrócić do audytu `docs/audits/001-output.md`, najpierw Slice 1:
   canonical `DailyDecision` dla Command Center.
