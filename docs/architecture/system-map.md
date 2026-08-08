# WILQ System Map — stan na 2026-08-08

Current-state dokument. To jest jedyna mapa architektury — opisuje, co żyje gdzie
i jak przepływa praca od ekologus.pl po bezpieczny szkic na dev. Decyzje i
historię trzyma git i Beads; ten dokument opisuje wyłącznie bieżący stan.

## 1. Czym jest WILQ — w jednym akapicie

WILQ to lokalny, API-first marketingowy system operacyjny dla Ekologus.
Czyta publiczną stronę ekologus.pl (production) i jej dev odpowiednik
ekologus.dev.proudsite.pl, zbiera dowody z GSC, GA4, Ahrefs, Google Ads,
Merchant Center i Localo, a na ich podstawie pomaga Wilku (marketerowi)
podejmować decyzje o treściach: co odświeżyć, co napisać, co zablokować.
Każda decyzja ma dowody (evidence) ze źródłem i okresem; każde twierdzenie
w tekście ma ślad do materiału źródłowego (claims); żaden zapis do
WordPressa nie dzieje się bez ActionObject: podgląd → review człowieka →
potwierdzenie → create-only szkic na dev z readback digest.

## 2. Warstwy

```text
dashboard (React/TS) + skills (Codex operator)
        │  HTTP, jedynie render typowanych kontraktów
        ▼
WILQ API (FastAPI) — publiczna granica, view models, 124 endpointy
        │
        ▼
domena (wilq/) — polityka, decyzje, evidence, knowledge, actions, audit
        │
        ├── content/   — pipeline treści (workflow, planning, drafts, quality)
        ├── briefing/  — powierzchnie decyzyjne (diagnostics, command center)
        ├── actions/   — ActionObject lifecycle (validate→preview→review→apply)
        ├── connectors/— adaptery read-only do systemów zewnętrznych
        ├── evidence/  — ślad dowodowy (metric facts, freshness)
        ├── knowledge/ — karty wiedzy, source facts/materials
        ├── storage/   — SQLite (stan) + DuckDB (metryki)
        ├── audit/     — niezmienny ślad zdarzeń
        └── codex/     — app-server seam dla Codex (run ledger, context)
        │
        ▼
systemy zewnętrzne (read-only): GSC, GA4, Ahrefs, Ads, Merchant, Localo,
WordPress (odczyt publiczny + create-only draft na dev)
```

Zasada: dashboard i skills konsumują TYLKO typowane kontrakty z API; nigdy
nie re-wyliczają stanu ani nie mają lokalnych map statusów. Jedna prawda =
kontrakt (`wilq/schemas/` + `packages/shared-schemas/`).

## 3. Przepływ danych A-Z (główna ścieżka treści)

1. **Źródła**: `connectors/` czyta (read-only) publiczne strony ekologus.pl,
   dev (ekologus.dev.proudsite.pl), GSC, GA4, Ahrefs, Ads, Merchant, Localo.
   Wynik to `MetricFact` + `Evidence` — zawsze ze źródłem, okresem, freshness.
2. **Dowody**: `evidence/` + `storage/metric_store.py` (DuckDB) trzymają
   agregaty z lineage; surowe payloady vendorów nigdy nie są persistowane.
3. **Decyzja**: `briefing/` (diagnostics, command center) i `content/planning/`
   budują work itemy i rekomendacje. Każde źródło ma status:
   `used | missing | stale | blocked | not_applicable | not_matched`.
   Brak dowodu = typed blocker, nigdy zgadywana metryka.
4. **Plan treści**: `content/planning/` (input_sources, dynamic_input,
   generated_proposal) — exact PageMaterial match z GSC/GA4/Ahrefs/Ads.
5. **Dokument**: `content/workflow/` — operator journey (5 kroków:
   scope → section_map → draft → review → dev_draft). Rewizja jest
   immutable (content_digest), każda sekcja ma evidence lineage.
6. **Review człowieka**: `content/quality/` (semantic review) + dashboard
   review workspace: decyzja pierwsza, pełny podgląd strony, claim ledger
   (które twierdzenia mają dowody), advisory w jednym disclosure.
7. **Create-only dev draft**: `content/handoff/` + `connectors/wordpress/` —
   ActionObject (validate→preview→review→confirm→apply) tworzy SZKIC na
   ekologus.dev.proudsite.pl. ACF: pełny clone zachowuje wszystkie layouty,
   sibling fields, media, repeatery. Po create: readback z digest
   (content exact, ACF subset-match).
8. **Audyt**: każda mutacja (nawet create-only) ma `audit/` wpis z
   event_type, trace, adapter, external_write_attempted.

## 4. Glosariusz nazw (jedno znaczenie, jedno słowo)

| Pojęcie | Znaczenie |
|---|---|
| PageMaterial | publiczna strona ekologus.pl (URL, tytuł, inventory, sekcje) |
| WorkItem | jednostka pracy nad jedną stroną (content_decision_{url}) |
| Revision | immutable wersja dokumentu (digest, sekcje, evidence, claims) |
| Claim | twierdzenie w tekście; status: allowed_with_evidence / blocked / blocked_until_measurement / allowed_general / needs_human_review; required = wymagane |
| Evidence | dowód (id, source_connector, freshness, okres) |
| MetricFact | pojedyncza metryka (source, period, value, freshness, evidence_id) |
| ActionObject | bezpieczna akcja (validate→preview→review→confirm→apply→audit); vendor write tylko przez adapter |
| Blocker | typed przeszkoda (code, label, reason, next_step) — nigdy cisza |
| OperatorJourney | 5 kroków: scope, section_map, draft, review, dev_draft |
| DevDraft | create-only szkic na ekologus.dev.proudsite.pl (nigdy publish/update/delete) |
| Readback | odczyt po create — dowód że treść dotarła (digest) |
| SourceFact | fakt z materiału źródłowego (approved/import_pending) |
| KnowledgeCard | zatwierdzona karta wiedzy o usłudze (service profile) |

## 5. Konwencje nazewnicze

- **Endpointy**: `/api/{domain}/{resource}` + akcja; work items pod
  `/api/content/work-items/{id}/...`; nowe strony pod
  `/api/content/new-page-briefs/{id}/...`; akcje pod `/api/actions/{id}/...`
  (validate, preview, review, confirm, apply, impact-check).
- **Moduły Python**: `wilq/{domain}/{subdomain}/module.py`; klasy `Content*`
  (np. `ContentDraftRevision`), funkcje `build_*` / `_private_*`.
- **Kontrakty**: modele w `wilq/schemas/` + mirror Zod w
  `packages/shared-schemas/`; dashboard importuje wyłącznie stamtąd.
- **Etykiety operatora**: polskie, API-owned (`*_label`), nigdy lokalne mapy
  w dashboardzie.
- **Testy**: Python w `tests/` (public contract + risk), dashboard
  `*.test.ts(x)` przy surface.

## 6. Mapa plików (co żyje gdzie)

```text
apps/api/wilq_api/routers/        — 30+ routerów, 124 endpointy
wilq/content/workflow/            — operator journey, revisions, workspace,
                                    target discovery/mapping, store
wilq/content/planning/            — input_sources, dynamic_input, proposals
wilq/content/drafts/              — draft package, structured generation
wilq/content/quality/             — semantic review, editorial integrity
wilq/content/handoff/             — dev draft handoff (create-only)
wilq/briefing/                    — diagnostics (ads, merchant, ahrefs, ga4),
                                    command center, tactical queue
wilq/actions/                     — ActionObject lifecycle + mutation readiness
wilq/connectors/                  — google_ads, wordpress, ahrefs, merchant,
                                    localo, gsc, ga4 (read-only adaptery)
wilq/storage/                     — SQLite state, DuckDB metrics, schema v.
wilq/audit/                       — event stream, identity
wilq/codex/                       — app-server seam (run ledger, context pack)
apps/dashboard/src/routes/        — 6 powierzchni + Zaplecze (Wiedza, Źródła)
apps/dashboard/src/components/    — panele prezentacji
packages/shared-schemas/src/      — kontrakt Zod (jedyna prawda dla UI)
.agents/skills/wilq-*/            — 13 operator skills (API-owned)
scripts/                          — verify.sh, test.sh, quality.sh, security.sh
```

## 7. Największe pliki — znane hotspoty (renowacja FAZA 2)

- `wilq/briefing/ads_diagnostics.py` 6265 linii — do rozbicia per-decyzja
- `wilq/briefing/merchant_diagnostics.py` 3342
- `wilq/briefing/command_center.py` 2751
- `wilq/connectors/google_ads/client.py` 2579
- `wilq/briefing/ahrefs_diagnostics.py` 2199
- `wilq/schemas/ads.py` 2137
- `wilq/actions/content_refresh.py` 2052
- `apps/dashboard/src/routes/GenericSurface.tsx` 1608
- `apps/dashboard/src/routes/MerchantDiagnosticSurface.tsx` 1215
- `apps/dashboard/src/lib/api.ts` 1069

## 8. Bezpieczeństwo i granice (nie negocjowalne)

- Zero vendor write poza create-only dev draft (ActionObject).
- WordPress: exact revision, draft-only; publish/update/delete NIEdostępne.
- ACF ≠ the_content: pełna strona przez page-level patch, nigdy przypadkowy
  message.content.
- Sekrety: tylko `.env` (lokalny); nigdy w artefaktach, promptach, docs.
- Brak dowodu/freshness = typed blocker.
- Zewnętrzne wejścia = niezaufane do walidacji i redakcji.

## 9. Bramki jakości

`scripts/verify.sh`: lint (ruff/eslint), mypy, typecheck, security scan,
1615+ testów backend, API smoke, skill smokes, 19 E2E, build dashboard.
`scripts/quality.sh`: skill hygiene + marketer language guard + typecheck.
Beads = tracker zadań; jeden in_progress; commit+push po akceptacji review.
