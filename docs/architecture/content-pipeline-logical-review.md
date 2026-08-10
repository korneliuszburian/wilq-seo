# WILQ Content Pipeline — logiczny re-review architektury

Rola dokumentu: `decision/reference`. Fixed point: `a783efe0f506ff8ada63f2f8b21f19701abb385c`
(`main`). Working tree: `.beads/issues.jsonl` (staged, user-owned) + 2 untracked
artefakty discovery z tej samej sesji; sam review nie modyfikuje kodu.

Proces: niezależny, read-only review architektury i jakości. Reviewer nie
wprowadza zmian (Codex jest executorem). Wszystkie hipotezy zweryfikowane w
kodzie na aktualnym fixed poincie; historyczne packety traktowane wyłącznie jako
wskazówka. Brak wartości `.env`, tokenów, surowych vendor payloadów i credential
paths w tym dokumencie.

---

## 1. Werdykt

- **REPAIR** — obecny pipeline może bezpiecznie przygotować pełny draft
  `the_content` na dev (create-only granica stoi, H1 strip działa, source
  niezmienny), **ale** nie spełnia definicji ACCEPT: istnieją reprodukowalne
  defekty logiczne decyzyjności (decyzja „ready" bez potwierdzonego inventory,
  GA4 strukturalnie odrzucane, service binding przez fuzzy keyword overlap,
  readback bez dowodu dokładnej treści).
- **ACF nie jest gotowe do pełnego page-level delivery**: brak guarda na
  zdegradowany fallback (`dev_draft_action.py:296-306`), preview i confirm digest
  pokrywają tylko deltę zamiast pełnego klonu (D2), readback nie dowodzi
  zawartości (D1), REST OPTIONS nie waliduje payloadu (P2).

Twierdzenie: żaden z poniższych defectów nie łamie dziś granicy bezpieczeństwa
(create-only, source immutable, brak publish). Wszystkie łamią **decyzyjność i
uczciwość** pipeline — dokładnie to, co marketer ma rozumieć w 30 sekund.

---

## 2. Production findings

### 2.1 HIGH — Decyzja „ready" dla URL bez potwierdzonego inventory; jedyny stop to syntetyczny always-on „duplicate risk"

**Miejsce**
- `wilq/content/planning/decisions.py:342-347` — `content_decision_status` zwraca `"ready"`
  dla `merge_create_after_inventory_check` (blokuje tylko `inventory_check_before_create`
  i `block_as_tracking_not_content`).
- `wilq/content/planning/decisions.py:152-169` — `merge_create_after_inventory_check`
  jest wybierane dokładnie gdy `wordpress_match == "missing"` i `query_count > 1`.
- `wilq/content/workflow/decision_mapping.py:182-187` — `_inventory_status` zwraca
  `"resolved"` gdy `final_canonical_url` jest ustawiony, **mimo że**
  `inventory_gate_status == "missing_inventory_match"`; w ten sposób twardy blocker
  `missing_inventory_resolution` (`wilq/content/workflow/models.py:194-203`) nigdy nie odpala.
- `wilq/content/workflow/decision_mapping.py:198-207` — `_duplicate_status` mapuje
  statyczny gate `"manual_merge_or_create_review"` na `"risk_found"` **bezwarunkowo**
  → twardy blocker `duplicate_or_canonical_risk` (`models.py:223-236`).
- `wilq/content/preflight/marketer_view.py:75` — karta marketera kopiuje `decision.status` (`"ready"`).

**Reproducer** — wejście: GSC facts dla `https://www.ekologus.pl/nieistniejaca-strona/`
z zapytaniami `["zapytanie alfa","zapytanie beta"]`; fakt WordPress tylko dla innego URL.
Obserwacja: `decision.status == "ready"`, `marketer_decision.status == "ready"`,
`mode_label "sprawdzić duplikację"`, `inventory` na work itemie „resolved",
`wordpress_match == "missing"`. Jedyny powód, dla którego candidate kolejki kończy
`recommended_mode: block`, to zawsze-obecna etykieta `duplicate_or_canonical_risk`.

**Impact marketera** — karta „ready" dla adresu, którego inventory nie potwierdziło;
syntetyczny „duplicate risk" dla każdej multi-query strony bez potwierdzenia WP;
preflight `review_required` (nie blocked) dla tego typu → staje się głównym itemem
pracy. Powierzchnia „ready" zaprzecza zablokowanej kolejce.

**Najmniejsza naprawa** — `decisions.py:345`: dodać `merge_create_after_inventory_check`
do zbioru `blocked` LUB w `decision_mapping.py:182-187` wymagać
`inventory_gate_status == "confirmed_current_inventory"` dla `"resolved"` (usunąć
escape `final_canonical_url`).

**Falsifier** — `content_decision_status("merge_create_after_inventory_check") == "blocked"`;
end-to-end: reproducer → `decision.status == "blocked"` i `marketer_decision.status == "blocked"`.

---

### 2.2 HIGH — GA4 exact landing facts strukturalnie odrzucane; kolejka zawsze projektuje GA4 „missing"

**Miejsce**
- `wilq/briefing/tactical_queue.py:501` — `item_facts = [*group_facts[:6], *([wordpress_fact] ...)]`
  (wyłącznie GSC + WordPress).
- `wilq/content/planning/decisions.py:257-262` — `metric_facts = sorted(...)[:8]` budowane
  tylko z tych `item_facts`; GA4 nigdy nie wchodzi do decyzji GSC.
- `wilq/content/workflow/queue.py:413-452` — `_ga4_metrics_for_decision` filtruje
  `decision.metric_facts` na `source_connector == "google_analytics_4"`; przy braku
  GA4 w faktach zawsze `status="missing"`, `evidence_ids=[]` — nawet gdy metric store
  ma exact `landing_page` fact dla tego URL.
- Kontrast: `wilq/content/workflow/inventory_binding.py:187-198` jawnie dokleja GA4 —
  projekcja działa tylko dla catalog-selected items, nie dla głównej kolejki diagnostycznej.

**Reproducer** — wejście: GA4 `sessions` fact z `landing_page == page` obecny w metric store;
decyzja zbudowana z GSC + WP. Obserwacja: `candidate.ga4_metrics.status == "missing"`,
GA4 nieobecny w `decision.evidence_ids`. Test `tests/content/test_content_work_item_queue_api.py:197-248`
dowodzi tylko filtra na ręcznie podanej decyzji zawierającej GA4; brak testu, że GA4
dociera do decyzji z realnego buildu.

**Impact marketera** — sygnały behawioralne (zaangażowanie na landing) zawsze „missing"
na głównej kolejce nawet gdy obecne i exact-matched; etykieta „missing" aktywnie myli.
Connector widnieje w `source_connector_labels`, a wnosi zero evidence do każdej decyzji GSC.

**Najmniejsza naprawa** — w `build_content_diagnostics`/`gsc_content_decisions` dołączać
GA4 facts z `metric_dimensions_match_landing(decision.page)` do `decision.metric_facts`
i `evidence_ids` przed projekcją kolejki.

**Falsifier** — reproducer → `candidate.ga4_metrics.status == "available"` oraz
`"ev_ga4_*" in candidate.ga4_metrics.evidence_ids`.

---

### 2.3 HIGH — Service cards przypinane do strony przez fuzzy keyword overlap (GSC queries i pełny body), nie exact canonical binding

**Miejsce**
- `wilq/content/knowledge/cards.py:486-499` — `text_values` zawiera: `topic`, H1/title,
  URL-e, **każdy GSC query dimension** (`fact.dimensions.get("query")`), evidence IDs,
  connector IDs.
- `cards.py:511-515` — pełny `wordpress_content_text` dołączany gdy
  `extraction_region == "wordpress_rest.content"` (standardowy region dla REST reads,
  `wilq/connectors/wordpress/client.py:1035`).
- `cards.py:769-823` — `_matching_service_candidates` przez `normalized_term_matches`;
  ranking preferuje exact URL jako pierwszy klucz, potem keyword/priority.
- `cards.py:826-845` — `_service_match_is_specific` akceptuje **jeden** termin ≥ 8 znaków
  lub dowolne dwa terminy; matcher `text_matching.py:18-49` jest fuzzy (prefix/≥5-overlap,
  ratio 0.75).
- Wiązanie napędza claims/CTA (`work_item_service_profile.py:151-193`), planning source
  facts (`input_sources.py:552-576`) i brief service fit.

**Reproducer** — strona `kariera` z GSC query `"bdo ewidencja odpadów"` lub z body
`"ewidencja odpadów"` wiąże `ekologus_service_bdo_reporting`; query
`"magazynowanie odpadów"` wiąże kartę waste-packaging. Etykieta reason sama to przyznaje:
`"Temat lub adres strony zawiera dokładną frazę …"` (`work_item_service_profile.py:315-318`).
(Guard jedno-słowny `cards.py:845` poprawnie odrzuca samo `"bdo"` — potwierdzone.)

**Impact marketera** — strona, która jedynie *rankinguje za* frazę usługową lub ją
*wspomina*, dziedziczy allowed/forbidden claims i CTA tej karty (np. kariera dostaje
CTA BDO). „Fit usługi" wygląda evidence-driven, a jest stem matchiem po demand queries
i chruście body.

**Najmniejsza naprawa** — usunąć GSC query strings z `text_values` (`cards.py:492-495`)
oraz gate body-text na URL z `source_lineage` karty (usunąć blanket
`wordpress_rest.content` z `cards.py:511-515`); keyword overlap tylko jako `candidates`
wymagające `service_selection_confirmed`.

**Falsifier** — reproducer → `match.service_card is None` i `service_candidates == []`.

---

### 2.4 MEDIUM — Brak danych Ahrefs renderowane jako liczba `0` („Luki Ahrefs powiązane z WordPress: 0")

**Miejsce** — `wilq/content/view_models/summary.py:82-90` (funkcja zwraca `0` gdy brak
`review_ahrefs_gap_records` decision) i `summary.py:73-78` (tile zawsze emitowany).
Test `tests/content/test_view_model_summary.py:125-131` wprost asertuje domyślne `0`.

**Impact marketera** — operator nie odróżnia „zero luk" od „Ahrefs brak danych / nie
podłączony". To dokładnie przypadek „missing data jako zero" zakazany przez politykę metryk.

**Najmniejsza naprawa** — zwracać `None`/pomijać tile przy braku decyzji Ahrefs (albo
etykieta „brak danych Ahrefs").

**Falsifier** — summary z decyzji bez `review_ahrefs_gap_records` → tile nieobecny/`None`,
nie `0`.

---

### 2.5 MEDIUM — Readback po create nie dowodzi dokładności treści (obie ścieżki)

**Miejsce**
- `wilq/connectors/wordpress/client.py:586-640` (`read_wordpress_draft_post`),
  `client.py:1088-1118` (`_draft_post_readback`) — zwraca tylko `content_summary`,
  `content_word_count`, `acf_field_count`, `acf_field_names`, `modified_gmt`.
- `wilq/content/workflow/stage_activation.py:33-88` — powierzchnia readbacku z tymi
  samymi licznikami; tekst blockerów przyznaje „Nie traktuj samego ID jako potwierdzenia
  treści" (`:70-71`), lecz readback też nie dowodzi równości.
- Mechanika digest istnieje (`client.py:822-824` `_wordpress_draft_value_digest`) i jest
  używana **tylko** w ścieżce trash (`client.py:643-679`), porównując WordPress-current
  vs WordPress-previous, nigdy stored-vs-sent.

**Reproducer** — create draft → readback. Vendor-side normalizacja (np. `wpautop`,
zamiana cudzysłowów, błąd mapowania, który zapisał inne pole) daje wciąż zgodne
`acf_field_count`/`content_word_count`/`content_summary`; **żadna asercja w repo nie
może tego złapać**. Wynik „created" (`dev_draft_execution.py:51-63`) zapisywany bez
weryfikacji.

**Impact marketera** — WILQ pisze „utworzono szkic" i audit pokazuje
`external_write_attempted=True` z ID, ale treść nigdy nie jest dowiedziona jako równa
approved revision. Uszkodzony/częściowy/nadpisany draft niewidoczny aż Wilku otworzy
edytor dev.

**Najmniejsza naprawa** — po create odczytać `content.raw` + `acf` i porównać
`_wordpress_draft_value_digest(...)` każdego z digestami wysłanego payloadu; mismatch →
blocker (lub `created_with_verification_blocker`).

**Falsifier** — mock: POST zwraca ID, GET zwraca content/ACF różne od wysłanego →
akcja nie może raportować niezweryfikowanego „created".

---

### 2.6 MEDIUM — ACF draft-preview i jego confirm digest pokrywają tylko deltę, nie pełny klon

**Miejsce**
- `wilq/content/workflow/target_mapping.py:589-607` — preview zwraca tylko zmapowane
  pola; `target_mapping.py:608-630` — digest nad `components` (revision + target digest +
  confirmation digest + root + components), nie nad pełnym payloadem.
- `target_mapping.py:634-641` — caveat „pozostałe pola zachowane" istnieje tylko dla
  `selected_components`; dla `full_document` brak go.
- `wilq/content/workflow/dev_draft_action.py:296-306` — zapisywany payload = **pełny
  clone** przez `_compile_current_acf_clone` (hero, media, contact rows bez zmian).
- `apps/dashboard/src/routes/ContentDocumentWorkspaceCanvas.tsx:188-268` — UI renderuje
  tylko `preview.components`.

**Reproducer** — ACF target z layoutem zawierającym hero row (image/background_type) i
contact row; zmapowana tylko sekcja body. Draft-preview pokazuje jeden replacement field;
utworzony draft zawiera także hero i contact — bez żadnego operator-facing renderu na
etapie preview/review/confirm.

**Impact marketera** — Wilku zatwierdza preview **delty** i dostaje draft z
niesprawdzonym contentem źródłowym. AGENTS.md „lead with the decision … evidence
summary" naruszone, bo deliverable jest większe niż potwierdzony zakres. Digest
binding nie obejmuje pełnego payloadu (źródło przypięte tylko tranzytownie przez
`source_acf_digest`/`fields_digest` przy apply).

**Najmniejsza naprawa** — dla `full_document` ACF: dodać renderowany summary
zachowanych (niezmienionych) wierszy/pól + caveat jak w `selected_components`; lepiej:
rozszerzyć preview/digest o digest skompilowanego pełnego payloadu przy tworzeniu akcji.

**Falsifier** — asercja, że `full_document` ACF draft-preview zawiera widoczną listę/liczbę
zachowanych wierszy/pól, a zmiana niezmienionego sibling field zmienia digest preview.

---

### 2.7 MEDIUM — Legacy handoff dostarcza dokument WRAZ z H1; nowa ścieżka stripuje H1

**Miejsce**
- `wilq/content/handoff/wordpress_execution.py:307-310` — `content_html=revision_document_html(document)`
  (H1 obecny, `revision_document_renderer.py:13-34`).
- `wilq/connectors/wordpress/client.py:489-491` — `content = content_html ...`, bez strip.
- vs `wilq/content/workflow/delivery_projection.py:33-41` — `wordpress_post_content_html` stripuje.
- Adapter nadal zarejestrowany (`registry.py:215`) i wykonywalny przez
  `execute_content_wordpress_draft_handoff(mode="live")` (`wordpress_mutation_requirements.py:414-465`)
  dla `act_apply_wordpress_draft_handoff`.

**Reproducer** — apply legacy handoff action dla natywnego posta (pełny łańcuch +
`WORDPRESS_EKOLOGUS_ALLOW_DRAFT_WRITES`). Draft dev zawiera `<h1>…</h1>` oraz motyw
renderuje tytuł jako H1 → **duplikat H1**. Ta sama approved treść przez target-mapping
ma H1 usunięty. `duplicate_h1` jest nawet rozpoznawanym kodem defektu w discard
(`dev_draft_discard_action.py:51`).

**Impact marketera** — identyczna approved treść ląduje inaczej w zależności od adaptera;
draft z podwojonym H1 wymagający ręcznego discard.

**Najmniejsza naprawa** — route legacy path przez `wordpress_post_content_html` lub
block `authoring_mode != "wordpress_post_content"` na legacy adapterze.

**Falsifier** — test, że legacy `ContentWordPressDraftPayload` → `create_wordpress_draft_post`
body nie ma wiodącego `<h1>` dla dokumentu, który od niego zaczyna.

---

### 2.8 LOW/MEDIUM — Dashboard re-derivuje gate dev-draft z `status === "approved"` zamiast API journey

**Miejsce**
- `apps/dashboard/src/routes/ContentDocumentWorkspaceCanvas.tsx:45,50,136,145` — mapping i
  draft-preview otwierane gdy `workspace.canonical_document.status === "approved"`.
- API prawda jest surowsza: `wilq/content/workflow/operator_steps.py:606-616` — blocker
  `missing_revision_bound_wordpress_seam` („Zatwierdzenie konkretnej wersji nie jest
  jeszcze zgodą na zapis do WordPress"); fakt `revision_bound_wordpress_handoff_ready`
  (`snapshot_assembly.py:478-481`).
- Grep `revision_bound_wordpress_handoff_ready` w `apps/dashboard/src` → **zero hitów**.

**Impact marketera** — marketer może otworzyć mapping/draft-preview i inwestować czas w
bindingi dla zatwierdzonej rewizji, którą API journey blokuje na kroku dev_draft. To
defekt UX/prawdy workflow, nie luka bezpieczeństwa zapisu (apply pozostaje server-gated).

**Najmniejsza naprawa** — eksponować `dev_draft_can_open`/`dev_draft_blocker` na
`ContentSelectedWorkspace` z tych samych factów (`selected_workspace.py:45-74`) i gating
na to, nie na `status === "approved"`.

**Falsifier** — test dashboardu: `<details>` dev-mapping nie renderowany, gdy API raportuje
krok dev_draft blocked mimo `status === "approved"`; zachować istniejący server-side test
`missing_revision_bound_wordpress_seam`.

---

### 2.9 LOW — Operator journey (5 kroków) jest prawdą bez konsumenta

**Miejsce** — `wilq/content/workflow/operator_steps.py:115-313` buduje journey z
`status_label`/`blocker`/`safe_next_step`/`can_open`/`can_submit`; `snapshot_assembly.py:420-489`
składa; ale `apps/api/wilq_api/routers/content_workflow_http.py:25-152`
(`project_content_work_item_browser_snapshot`) **nie jest podłączone do żadnej trasy** (tylko
`__all__` i typ w `content_legacy_wordpress_read.py:15`). Dashboard renderuje model
document-first (3 zakładki + review), nie journey; grep `operator_steps|currentStepId`
w `apps/dashboard/src` → zero hitów.

**Impact marketera** — operator nigdy nie widzi step-level blockers („zakres zablokowany:
źródła briefu wymagają review" `operator_steps.py:352-358`; „plan sekcji zablokowany"
`:200-211`; „dev_draft zablokowany" `:606-616`).

**Najmniejsza naprawa** — podłączyć journey do istniejącego `selected-workspace` lub
nowego kontraktu, który dashboard już czyta; nie budować drugiej wersji w React.

**Falsifier** — test API, że `selected-workspace` zawiera `operator_steps` z
`current_step_id` i per-step `blocker`; test dashboardu renderujący ten blocker.

---

### 2.10 LOW — Lokalne mapy etykiet w React dublują API label (two-truth)

**Miejsce** — `apps/dashboard/src/routes/ContentDocumentWorkspaceCanvas.tsx:880-886`
(`sourceStatus()`/`documentStatus()`) używane w StatusCards (`:112-113`), podczas gdy
główna karta (`:76`) używa API `workspace.canonical_document.label`. Dwa źródła tej
samej etykiety.

**Impact marketera** — dryfowanie wersji polskiej etykiety, gdy API zmieni copy.
Kosmetyczne.

**Naprawa** — renderować API `label`/`reason`; usunąć lokalne mapy.

---

## 3. Potwierdzone właściwości (co realnie działa i na czym to oparto)

| Właściwość | Dowód |
| --- | --- |
| Source na ekologus.pl niezmienny | oba adaptery POST do collection bez ID (`client.py:482-491, 566-571`); jedyny ID-addressing to trash z `modified_gmt`+`content_digest`+`acf_digest` i `force=false` (`client.py:682-768`) |
| Create-only + draft-only granica | `WORDPRESS_DEV_HOSTS = {"ekologus.dev.proudsite.pl"}` (`client.py:55`), host checks (`:459-462, 521-524`), `create_only=True` + flagi w ACF (`:530-543`); payload type-locked (`dev_draft_action.py:66-74`) |
| ACF clone fail-closed na drift | `acf_clone_projection.py:57-97` — object/root/root_digest/fields_digest/layout/row/leaf checki przed write |
| Pełna ochrona sibling fields w clone | `test_acf_clone_projection.py:70-128` (top-level siblings preserved, ich drift blokuje) |
| Brak wpychania całego artykułu do jednego pola ACF | `_components` (`target_mapping.py:358-383`) nigdy nie zawiera `document-content` na ACF surface; guard `set(selections) ⊆ component_ids` (`:433`); `require_unique_leaf_replacements` (`acf_clone_projection.py:34-42`) |
| H1 strip w nowej ścieżce + digest z strippem | `delivery_projection.py:22-41` — `payload_digest` pokrywa stripped wartość (`target_mapping.py:608-630`); idempotentne |
| Exact lineage nieprzerwany (nowa ścieżka) | revision→review→confirmation→ActionObject→claim→draft→readback, każdy krok digest/decision-bound (`store.py:141-168, 407-439`; `store_revision_review.py:45-67`; `dev_draft_action.py:96-103, 532-555`) |
| Idempotencja apply/review/append | claim `ON CONFLICT(claim_key) DO NOTHING` + terminal statusy (`store.py:427-488`); review idempotentne (`store_revision_review.py:35-36`); append `stale_base`+digest (`store.py:147-168`); planning `enqueue` PK na input digest (`generated_proposal_store.py:529-538`) |
| Claim apply gated | `_binding_is_current_and_approved` (`store_queries.py:231-254`) + blokada append (`store.py:142`) i review (`store_revision_review.py:54`) — dwa `claimed` rzędy dla jednego work itema nieosiągalne przez API |
| Ahrefs typed cross-source | `ahrefs.py:467-499`, `ahrefs_overlap.py:172-201`; test `tests/content/test_ahrefs_planning.py:116-160` |
| Planning input assessments honest | `input_sources.py:315-358, 443-496, 731-769` — obecne-ale-nie-pasujące → typed `missing`/`blocked`/`stale`; `usable_query_portfolio` dropuje nie-`used` ale trzyma statusy |
| Freshness gating | `live_data_available` wymaga obu primary connectorów (`content_diagnostics.py:763-777`); brak decyzji bez primary data |
| Dashboard parse-every-response | `apps/dashboard/src/lib/api.ts` — każdy call kończy `schema.parse(...)` (`:254-328`); brak raw `.json()`/`as any` poza wrapperem |
| POST→GET planning state match | `content_planning_proposals.py:222-247` + `proposal_read.py:69-80` (ta sama queued response); idempotentny re-POST |
| Previewy API-backed | pełna strona = persisted `ContentDraftRevision`; draft-preview = `ContentTargetDraftPreview` z `payload_digest` gate |
| Brak wycieków `dict[str, Any]` w publicznych modelach | `wilq/schemas/content.py`, `contracts.py`, `queue.py:130-181` (tylko `connector_refresh_run_ids: dict[str,str]`, mirrory w TS) |

---

## 4. Proof gaps (wyłącznie luki dowodowe, nie defekty)

- **P1 — ACF zdegradowany fallback bez guarda** (`dev_draft_action.py:296-306`,
  `_acf_clone_plan` `:427-433`). Nieosiągalny przez obecne API (trace: brak digestów →
  `_acf_writable_fields={}` → `write_profile_status="unavailable"` → mapping blocker;
  brak `target_section_index` → validator confirmation blokuje). Ale **brak guarda** i brak
  falsifiera; jedyny test dotykający tego (`test_content_target_mapping.py:580-643`)
  asertuje **zdegradowany** output. Zmiana discovery (layouty bez section_index albo
  writable fields przy brakujących digestach) cicho aktywowałaby partial clone.
  Rekomendacja: `else → raise ValueError("Akcja szkicu ACF nie ma planu klonowania.")`.
- **P2 — REST OPTIONS schema to normalizacja, nie walidacja** (`client.py:266-303, 340-379`):
  `_acf_create_schema` tylko lokalizuje `endpoints[].args.acf` (wymaga `methods == ["POST"]`),
  `_normalize_acf_for_create` tylko zamienia empty string na null/omission; nieznane typy i
  niezgodne kształty przechodzą do vendor 400. Dodatkowo `acf_rest_schema.py:149-184` czyta
  item OPTIONS, `client.py:276-300` collection OPTIONS — dwa zakładane kształty.
- **P3 — readback nie sprawdza `status == "draft"` ani identity** (`client.py:1097-1104`
  fallback do requested ID bez porównania). Niskie ryzyko (ID z create response).
- **P4 — H1-strip regex tylko wiodący `<h1>`** (`delivery_projection.py:5-8`); prawdziwe dla
  canonical output dziś, ale zmiana renderera (wrapper div, blockquote, komentarz) cicho
  produkuje duplikat H1. Brak falsifiera dla nie-wiodącego H1.
- **P5 — `contentWorkflowDraftSectionModel.ts`** (21 linii) — martwy kod (zero importów);
  latentny two-truth: `sectionOverrideKey` normalizuje case/whitespace, podczas gdy API
  porównuje nagłówki exact (`content_workflow.py:388,404-412`). Usunąć albo przenieść
  kluczowanie do API.
- **P6 — TS `preflight_status: z.string()`** (`contentWorkflow.ts:246`) luźniejsze niż
  Python enum (`queue.py:151`) — klient nie złapie dryfu enuma. Zacisnąć do
  `ContentPreflightStatusSchema`.
- **P7 — brak testu pinującego `content_decision_status("merge_create_after_inventory_check")`**
  (`tests/content/test_planning_decisions.py` asertuje tylko `refresh_or_merge→ready`
  i `inventory_check_before_create→blocked`). Dlatego 2.1 przechodzi CI.
- **P8 — GA4 queue projection testowana tylko na ręcznie zbudowanej decyzji**
  (`test_content_work_item_queue_api.py:197-248`); end-to-end z diagnostics nie testowany.
  Dlatego 2.2 przechodzi CI.
- **P9 — `tests/content/test_content_diagnostics.py` nie istnieje** (jest
  `tests/test_content_diagnostics.py` — cache/freshness/ranking, nie semantyka statusów
  per connector).
- **P10 — race/pipeline**: patrz §D — te nie są „brakiem testu", ale wymagają
  deterministycznego falsifiera z kontrolowanym zegarem/barierą, zanim uznamy je za
  zamknięte.

---

## 5. Migration extraction ledger

| Moduł | Kategoria | Uzasadnienie | Zależność | Ryzyko |
| --- | --- | --- | --- | --- |
| `wilq/connectors/wordpress/client.py` (REST read + create-only + readback + trash) | **portować** | czysty kontrakt, testy, create-only | `wilq/credentials/runtime.py` | niskie |
| `wilq/connectors/{gsc,ga4,ads,merchant,ahrefs,localo}/client.py` | **portować** | read-only, testowane | Google creds group, OAuth | niskie |
| `wilq/evidence/registry.py` | **portować** | deterministyczna projekcja | metric store | niskie |
| `wilq/security/redaction.py` | **portować** | silne redaction, allowlist digestów | — | niskie |
| `wilq/content/workflow/{revisions,store,store_revision_review,store_schema,revision_persistence,revision_children}.py` | **portować** | append-only + claim, server-owned | `wilq/storage/local_state.py` | średnie (payload-based) |
| `wilq/content/workflow/{target_discovery,target_mapping,acf_clone_projection,dev_draft_action,dev_draft_execution}.py` | **portować** (po naprawie 2.5/2.6/2.7/P1) | ACF + create-only | snapshot read-only | średnie |
| `wilq/actions/{apply_lifecycle,action_blockers,mutation_contract,wordpress_mutation_requirements,audit_store}.py` | **portować** | ActionObject safety | audit | średnie |
| `wilq/credentials/runtime.py` | **portować** | secrets provider, names-only | — | niskie |
| `apps/api/wilq_api/routers/content_*.py` (aktywne) | **portować** | cienkie, server-owned | domena | niskie |
| `wilq/schemas/` + `__init__.py` (frozen) | **wydzielić i uprościć** | rozbić na domenowe schemas | TS mirror | średnie (sync) |
| `wilq/actions/service.py` (frozen) | **wydzielić** | rozbić | — | średnie |
| `wilq/briefing/content_diagnostics.py` (frozen monolit) | **wydzielić** | rozbić na decyzje | — | średnie |
| `tests/test_api_contracts.py` (50KB) | **wydzielić** | rozbić na domenowe pliki | — | niskie |
| `wilq/content/workflow/store.py` | **wydzielić** | duży, wiele odpowiedzialności | — | średnie |
| `apps/api/wilq_api/context_*.py` + `context_cache.py` | **wydzielić** | przenieść do `wilq/codex/` | — | niskie |
| `wilq/codex/app_server.py` | **referencja** | wzorzec sandbox/approval | `codex` CLI | niskie |
| `wilq/content/workflow/operator_steps.py` | **referencja → port** | dobra domena, brak konsumenta (2.9) | — | niskie |
| `wilq/content/planning/{input_sources,dynamic_input,section_mapping}.py` | **portować** | honest typed assessments | — | niskie |
| `wilq/content/workflow/decision_mapping.py` | **referencja → port** | po naprawie 2.1 | — | niskie |
| `wilq/content/knowledge/cards.py` (service matcher) | **referencja → port** | po naprawie 2.3 | — | wysokie (jeśli zostanie) |
| `wilq/connectors/{linkedin,facebook}/` stubs | **usunąć** | brak adaptera, ryzyko > wartość | decyzja ownera | niskie |
| legacy WP paths (`WORDPRESS_EKOLOGUS_SSH_*`, `WP_CLI_*`, `HELPER_PLUGIN_*`, `DOCROOT`, `AUTHORING_TARGET`) | **usunąć** | dowód braku callera | audyt | niskie |
| legacy aliases env (`EKOLOGUS_WP_STAGING_*`, `MIS_*`) | **usunąć** | duplicate identity | names-only audit | niskie |
| `docs/handoffs/`, `docs/review-packets/` historyczne | **archiwum** | historyczne narracje | — | niskie |
| `PLAN.md`/`PLANS.md` | **konsolidacja** | kompetujące plany | — | niskie |
| `contentWorkflowDraftSectionModel.ts` | **usunąć** | martwy kod, latentny two-truth (P5) | — | niskie |
| GraphQL / pełny rewrite | **odrzucić** | brak konkretnego problemu nie dającego się naprawić ewolucyjnie | — | wysokie |

---

## 6. Pierwszy rekomendowany slice (po tym review)

```text
read-only PageMaterial → native the_content revision → human review
→ create-only dev draft → exact readback
```

### Publiczny kontrakt
- `GET /api/content/work-items/{id}/selected-workspace` (istnieje) rozszerzony o
  `operator_steps` (journey z blockerami) — naprawa 2.9 + 2.8.
- `POST /api/content/work-items/{id}/initial-draft` → `ContentDraftRevision` (istnieje).
- `POST .../draft-revisions/{rev}/review` exact digest (istnieje).
- `POST .../target-mapping/confirmation` + `draft-action` → ActionObject (istnieje).
- `POST /api/actions/{id}/apply` → create-only draft (istnieje).
- **Nowe**: post-create readback digest w `wordpress_draft_readback` — naprawa 2.5
  (dla `the_content` wystarczy sha256 rendered/content).

### Testy, które muszą przejść
1. 2.1: `content_decision_status("merge_create_after_inventory_check") == "blocked"`
   i end-to-end `marketer_decision.status == "blocked"` dla URL bez WP match.
2. 2.5: mock POST→GET różny content → nie „created"; poprawny content → `created` z digest.
3. 2.8/2.9: `selected-workspace` zawiera `operator_steps`; dashboard renderuje blocker
   dev_draft; `<details>` dev-mapping zablokowany mimo `status === "approved"`.
4. 2.7: legacy payload bez wiodącego H1.
5. 2.3: strona `kariera` z GSC query „bdo ewidencja odpadów" → `service_card is None`.
6. 2.2: GA4 exact landing → `candidate.ga4_metrics.status == "available"`.
7. 2.4: brak decyzji Ahrefs → tile nieobecny (nie `0`).

### Warunek ukończenia
- Cały łańcuch dla wybranej strony `the_content`: PageMaterial snapshot → revision →
  review → create-only draft → readback z digest equality; source niezmieniony.
- Read-only ACF discovery (OPTIONS + snapshot digesty) dla następnego slice'a.
- `scripts/lint.sh`, `scripts/typecheck.sh`, skupione testy content zielone (także w
  środowisku z `.env` — patrz P10/red gate z discovery).

---

## Załącznik D — zweryfikowane race/state (sekcja D promptu)

Potwierdzone samodzielnie na fixed poincie (nie przez stare packety):

| # | Race/defekt | Miejsce | Interleaving | Czy production defect |
| --- | --- | --- | --- | --- |
| 1 | Planning claim **process-local** | `content_planning_proposals.py:349-370` (`_PLANNING_ACTIVE_KEYS`, 2-thread executor) | A: POST enqueue; crash procesu przed release → klucz wisi; ratuje tylko stale-job TTL | **tak** (multi-worker/crash) |
| 2 | Snapshot staleness across queue | `content_planning_proposals.py:140-312` — snapshot wczytany, enqueue, claim, submit ze starym snapshotem; worker nie reloaduje | A: zmiana context między read a run | **tak** (łagodzone przez `for_input` idempotencję; brak context-guard jak initial-draft) |
| 3 | GET może pisać | `content_snapshot.py:196-230` → `read_content_planning_proposal` może utworzyć proposal w GET | dwa równoległe GET-y mogą enqueue | **tak** (idempotencja `for_input` ratuje; nadal GET-write) |
| 4 | Editor save bez context guard w tej samej transakcji | `content_workflow.py:139` → `append_draft_revision`; polega na `stale_base` + router `context_current` | context zmienia się między snapshot a append | **tak** (niższa, bo `stale_base` łapie latest) |
| 5 | `latest_human_review` na `rowid DESC` | `store.py:854-867` + upsert `ON CONFLICT(id) DO UPDATE` (`store.py:639-656`) | re-zapisany rząd o niskim rowid nosi nowszą treść; `rowid DESC` zwraca najwyższy rowid (stara decyzja) | **tak** (niskie; „latest" może kłamać na korzyść starej treści) |
| 6 | Claim apply gated | `store.py:407-412` `_binding_is_current_and_approved` | dwa apply różne binding → drugi `not_current`; ten sam → `in_progress` | **nie** (potwierdzone, patrz §3) |
| 7 | Initial draft executor unbounded queue | `content_initial_draft.py:56-62` max_workers=2, wewnętrzna nieograniczona kolejka | wiele submitów kumuluje się; queued run pokazuje „generating" do 900s | **tak** (niski) |
| 8 | Apply nieatomowy (okno 300s) | `store.py` claim → HTTP write → `finish_*`; crash w oknie = unresolved `claimed` | A: claim commit; proces umiera; B: retry przed reconcile | **tak** (łagodzone przez 300s reconcile; brak automatycznego retry) |
| 9 | New-page apply szersze okno: claim flip bez audytu | `store_new_page_apply.py:99-117` flipuje claim; router zapisuje audit w 2 połączeniach (`actions.py:322-325`) | crash między claim a router save → „applied" bez audytu | **tak** |
| 10 | Router double-persist audit | `actions.py:323-325` re-save audytu zapisanego przez `finish_wordpress_revision_apply_claim` (`store.py:534-535`) | redundantny, idempotentny upsert | **nie** (kosmetyka) |
| 11 | DuckDB delete-then-insert bez transakcji | `metric_store.py:91-114` (autocommit) | crash między DELETE a INSERT → partial/brak faktów, run `failed` | **tak** (niski) |
| 12 | LAG „previous" na ties | `metric_store.py:137-156` `ORDER BY collected_at ASC, evidence_id ASC`; evidence_id = hex uuid | dwa runy w tej samej sekundzie sortują się po losowym hex | **tak** (niskie) |
| 13 | Refresh enqueue TOCTOU | `refresh.py:211-244` check-then-insert | dwa równoległe queue → dwa queued runs; drugi re-run vendor read | **tak** (niski) |
| 14 | Caches process-local | `action_catalog.py:96`, `context_cache.py:15-16`, `content_diagnostics.py:120` | multi-worker dzielący ten sam sqlite → stale | **tak** (niski, single-process dziś) |
| 15 | Terminal replay po `applied` | `store.py:471-488` claim `applied`/`failed` → retry tylko `failed` bez external write | — | **nie** (potwierdzone) |

Uwaga: 1,2,3,7,9,11,12,13 wymagają deterministycznych falsifierów z kontrolowanym
zegarem/barierą/fake adapterem (patrz P10); nie wolno ich zgłaszać jako „brak testu".

---

## Załącznik — jakie ścieżki/dokumenty faktycznie przeczytano

- `AGENTS.md`, `docs/CONTEXT.md`, `docs/architecture/vnext-discovery-packet.md`,
  `docs/architecture/vnext-first-slice.md`, `docs/architecture/workflow-orchestration.md`,
  `docs/architecture/action-model.md`, `docs/architecture/connector-registry.md`,
  `docs/architecture/model-runtime-policy.md`, `docs/architecture/quality-gates.md`,
  `docs/current-cleanup-state.md`, `PLANS.md` (fragmenty).
- Kod: `wilq/content/planning/{decisions,input_sources,ahrefs,ahrefs_overlap}.py`,
  `wilq/content/workflow/{decision_mapping,store,store_new_page_apply,store_revision_review,
  queue,target_discovery,target_mapping,acf_clone_projection,dev_draft_action,
  dev_draft_execution,delivery_projection,operator_steps,snapshot_assembly}.py`,
  `wilq/content/knowledge/{cards,text_matching,work_item_service_profile}.py`,
  `wilq/briefing/{content_diagnostics,tactical_queue}.py`,
  `wilq/connectors/wordpress/client.py`, `wilq/connectors/refresh.py`,
  `wilq/storage/{metric_store,local_state}.py`,
  `wilq/actions/{apply_lifecycle,action_blockers,mutation_contract,wordpress_mutation_requirements,audit_store}.py`,
  `apps/api/wilq_api/routers/{content_planning_proposals,content_initial_draft,content_snapshot,actions,content_workflow,content_workflow_http}.py`,
  `apps/dashboard/src/{lib/api.ts,routes/ContentDocumentWorkspaceCanvas.tsx,routes/ContentWorkflowSurface.tsx,contentWorkflowQueries.ts,contentWorkflowDraftSectionModel.ts}`,
  `packages/shared-schemas/src/contentWorkflow.ts`.
- Testy: `tests/content/test_acf_clone_projection.py`, `test_content_target_mapping.py`,
  `test_content_work_item_queue_api.py`, `test_planning_decisions.py`,
  `test_ahrefs_planning.py`, `test_content_workflow_adversarial_gates.py`,
  `test_dynamic_planning_proposals_api.py`, `test_view_model_summary.py`,
  `tests/connectors/test_wordpress_draft_write.py`, `tests/test_content_diagnostics.py`.
- Runtime read-only: `scripts/local_stack.sh status`, `GET /api/health`, `GET /api/system/status`,
  `GET /api/connectors`, `GET /api/jobs/status`, `GET /api/metrics/status`,
  `GET /api/content/diagnostics` (decyzje 52/53 GSC+WP).
