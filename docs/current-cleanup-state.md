# Current Cleanup State — 2026-07-17

Przeczytaj przed cleanupem, refaktorem dashboardu albo zmianą kontraktu API.
Historia slice’ów jest w git i Beads; ten plik opisuje tylko bieżący stan.

## Najbliższa instrukcja

Po evidence-bound query mappingu, pełnym dokumencie i inventory-verified
linkowaniu dawny P0 `wilq-seo-1oa.36.23` jest już zamknięty po proofie redakcji
bezpieczeństwa. Aktualnie najwyższym bezpiecznym P0 z kolejki jest
`wilq-seo-1oa.36.14`: aktywacja trwałego semantic-review storage wymaga
backupu i maintenance window. `.36.22` wiąże WordPress execution readback z
exact revision handoff, a `.36.21` chroni historię measurement windows, jeśli
ich zależności zostaną odblokowane. Każdy slice pozostaje osobno claimowany i
proofowany; nie łącz tych władz w jeden cleanup.
Realne initial draft i semantic review nadal wymagają owner review obu kart, a
aktywacja storage wymaga backupu i maintenance window.
Seam aktywacji jest już jawny i nie jest wywoływany przez API: `uv run wilq
storage activate-semantic-review` wymaga osobnych ścieżek SQLite/DuckDB backupu
oraz `--approved-maintenance-window`; bez tej flagi nie modyfikuje storage.
Placement pełnego dokumentu nie ma fallbacku: nowy plan może wskazać tylko
`after_lead`, `after_content` albo dokładny nagłówek własnej sekcji, który przy
składaniu dokumentu staje się stabilnym `section_id`. Nieznana wartość blokuje
plan albo initial-draft zamiast zmieniać położenie CTA/linku.

`wilq-seo-1oa.36.5` rozszerza trwałą rewizję do pełnego dokumentu v2 bez
zmiany istniejącego journey. Rewizja obejmuje teraz title/meta/H1/lead, sekcje
ze stabilnymi ID, FAQ, CTA, linki wewnętrzne oraz exact digests planu, usługi i
inventory. Jeden digest obejmuje wszystkie te pola; zmiana dowolnego page assetu
unieważnia exact review. Stare rekordy v1 pozostają czytelne i zachowują swój
historyczny algorytm digestu. Revision-bound WordPress dry-run renderuje pełny
dokument, ale zachowuje meta pola jako `review_required` z typed blockerem,
ponieważ nie ma potwierdzonego mapowania ACF/SEO. Proof używa wyłącznie
tymczasowego SQLite; nie uruchamiaj migracji ani restartu realnego local state
bez backupu i maintenance window.

`wilq-seo-r564.10` domknął zwarty exact-revision flow człowieka w
`/content-workflow`: podgląd, review, potwierdzenie, kontrola bezpieczeństwa i
draft-only apply używają jednego API-owned bindingu. Tylko aktywny etap jest
rozwinięty. Resume czyta najnowsze uporządkowane eventy tej wersji, a typed
konflikt lub terminalny blocker zatrzymuje przebieg bez retry. Syntetyczny
browser proof przechodzi cały flow bez połączenia z WordPressem.

`wilq-seo-r564.11` domknął server-side handshake WILQ API → Codex app-server
przez istniejący `codex login`. API pobiera pełny typed model input oraz exact
base/review, a dynamiczne pola trafiają wyłącznie do `untrusted` context.
App-server działa ephemeral/read-only na izolowanym profilu, wyłącza znane
capabilities i unieważnia wynik po zaobserwowanej próbie tool/server request;
stockowy protokół nie daje jednak twardej gwarancji `tool-free`. Wynik może
  utworzyć tylko `unreviewed` child revision, a rewizja i terminalny run zapisują
  się atomowo z trwałym evidence/claim lineage. Quality dotyczy wyłącznie
  utrwalanych wybranych sekcji; obcy identifier, literalny known blocked claim i
  wąski high-risk promise guard są fail-closed. Persistowane advisory review
  wspiera decyzję o poprawce, lecz akceptacja semantyczna nadal należy wyłącznie
  do człowieka. Finalny proof po hardeningu
utworzył 38-słowną poprawkę sekcji na dwóch dowodach GSC/WP bez zaobserwowanej
próby tool call, ale quality uczciwie zwróciło
`needs_changes`; nie jest to dowód finalnej jakości tekstu. Browser nadal nie
rozmawia z Codex bezpośrednio, a Codex nie jest właścicielem workflow, approval
ani ActionObject.

`wilq-seo-r564.13` podłączył proposal do aktywnego kroku `draft`: Wilku wybiera
API-approved sekcje exact reviewed revision, widzi pending, diff baza/child,
lineage, findings i semantyczną bramkę review. Browser-safe snapshot nie zawiera
promptu ani model inputu. Marketerowy WordPress dry-run udający content review i
osierocone panele zostały usunięte. Desktop/mobile proof nie dotyka Codexa ani
WordPressa; exact proposal POST jest syntetycznie przechwycony.

`wilq-seo-r564.14` usuwa legacy OpenAI SDK/API-key runtime, pięć publicznych
dróg ujawnienia full generation contract oraz martwe browser schemas. OpenAPI
ma cztery ograniczone modelowe POST-y: exact section `codex-proposal`, versioned
`planning-proposals`, exact `initial-draft` oraz exact revision
`semantic-review`; wszystkie używają tego samego
server-side app-servera, a odczyty pozostają model-free. Internal structured contract/output i
preview blockers pozostają wymagane przez te seamy. Nie dodawaj
`OPENAI_API_KEY`, Agents SDK, Ollamy ani alternatywnej ścieżki modelu.

`c9h9.4` jest zamknięty i nie wolno go powtarzać. Po każdym slice uruchom
`bd ready --json`, zaktualizuj ten handoff, zrób świadomy commit/push i
kontynuuj najwyższy bezpieczny task.

## Prawda produktu

- Kanoniczny pilot jest bezwarunkowo loopback-only: manager stosu odrzuca
  non-loopback bind przed zmianą runtime, middleware sprawdza peer socket i nie
  ufa `Host`, a dawny env bypass nie działa. README nie promuje ręcznie
  uruchamianego Uvicorna/Vite. To nie jest dowód auth, TLS ani gotowości do
  zdalnego deploymentu.
- `/content-workflow` jest jedynym głównym workspace’em `Treści i SEO`;
  publiczny `ekologus.pl` pozostaje SEO truth, a Proudsite jest wyłącznie
  draft/dev workspace.
- Snapshot zachowuje pięć kontraktowych etapów `scope → section_map → draft →
  review → dev_draft`, ale `section_map` jest wyłącznie projekcją API. Gdy plan
  jest generowany, bieżący krok pozostaje uczciwie `scope`; po wygenerowaniu
  system przechodzi bezpośrednio do `draft`. Pierwszy zapis rewizji pozostaje
  zablokowany do aktualnej decyzji zakresu/usługi, nie do zatwierdzania nagłówków.
- Aktywny `scope` pokazuje jeden zwarty panel decyzji oraz podgląd mapy, gdy ta
  istnieje. Marketer nie zatwierdza kolejności, celu ani dowodów sekcji osobnym
  formularzem: mapa powstaje dynamicznie z odczytanego ACF albo `the_content`,
  inventory, usługi, zapytań i evidence. Konflikt zachowuje lokalną notatkę i
  wymaga jawnego odświeżenia.
- Scope pokazuje typed zapytania GSC z metrykami, okresem, freshness i
  konserwatywnym przypisaniem do sekcji. Same exact page i wspólny refresh-level
  evidence ID nie wystarczają już do przypisania query do każdej sekcji. Ogólny
  mapper intencji rozróżnia definicję, zastosowanie, obowiązek, proces, usługę i
  lokalność; przypisuje wyłącznie jedną najlepiej dopasowaną sekcję, a remis,
  obce miasto lub brak pokrycia pozostawia jako page-level evidence. Typed
  `section_mapping_status` i polska etykieta UI ujawniają aktualne
  `intent_relevance`, historyczne `lexical_relevance` oraz `page_only`.
  Ads i Keyword Planner nie są zgadywane:
  pojawiają się tylko przy exact term+page+service. Live proof obu pilotów
  rozdziela BDO applicability oraz ogólne i lokalne zapytania outsourcingu;
  nieobsługiwane miasta pozostają `page_only`.
- `wilq-content-operator` prowadzi jeden kanoniczny kontrakt API: wybór exact
  work itemu, baseline scope/service review, ponowne zbudowanie planning inputu,
  jawne wygenerowanie planu, review scope i section map, initial full draft,
  exact semantic review, poprawkę wybranych `section_id`, human review oraz
  revision-bound WordPress draft-only. Statusy GET pozostają model-free, a
  `stale` może wskazywać historyczną rewizję bez udawania aktualnego review.
  Skill nie rekonstruuje preflightu, briefu ani paczki marketera i nie ma direct
  WordPress execution. Dawny 809-liniowy `build_uat_packet.py` oraz duplikujący
  snapshot/export zostały usunięte bez zastępczego generatora; kanoniczna
  sanitizowana paczka pozostaje czterema dokumentami wynikowymi.
- Dynamiczne planowanie nie blokuje już wszystkich linków przez `maxItems=0`.
  `ContentPlanningInput` v3 zawiera wyłącznie kandydatury URL z kierunku
  widocznego w reviewed scope, które mają dokładny publiczny rekord WordPress i
  evidence z bieżącego wejścia. Schema modelu ogranicza URL i liczbę linków,
  lineage odrzuca obcy target/evidence/claim/placement, a zaakceptowany link
  zachowuje stabilne ID przez pełną rewizję, child revision i renderer
  WordPress. Brak potwierdzonego inventory daje zero kandydatur, nie zgadywany
  link.
- Publiczny WordPress inventory rozdziela bounded metadata enrichment per grupa
  `posts`, `pages` i pozostałe typy. Dzięki temu późniejsza w sitemapie strona
  doradztwa/outsourcingu ma exact canonical, tytuł/H1 i 12 obserwowanych H2/H3
  z aktualnym evidence zamiast samego URL; BDO pozostaje pokryte. Te nagłówki są
  publicznym inventory HTML, nie potwierdzonym readbackiem ACF —
  `wordpress_acf_section_inventory_status` nadal wynosi `missing`, a układ bez
  nagłówków nie dostaje wymyślonych sekcji. Klient konektora jest poniżej 800
  linii; inventory i wspólne czyszczenie tekstu mają osobnych właścicieli.
- Rewizja v2 przechowuje exact `planning_digest`, `planning_input_digest`,
  service/inventory digests i pełne page assets; te same bindingi przechodzą do
  child revision Codexa. Cofnięcie decyzji albo zmiana inventory, usługi,
  wiedzy lub metryk unieważnia review/handoff bez kasowania zapisanej wersji.
  Rewizje v1 pozostają czytelne na historycznym digescie, ale brak bieżącego
  bindingu nadal oznacza stale.
- Ocena 8/10 dotyczy wyłącznie bezpieczeństwa exact handoffu. Operator workflow
  ma obecnie około 6/10, ale jakość realnego tekstu pozostaje około 5/10:
  sekcję można już poprawić przez grounded Codex proposal i porównać wynik,
  lecz realny proof był generyczny i `needs_changes`. Nie claimuj jakości przed
  owner-reviewed Service Profile i testem paczki na konkretnej usłudze/sekcji.
- Marketer widzi stronę, usługę, decyzję, pięć zadań i jeden aktywny workspace.
  Dziewięć paneli technicznych nie istnieje w marketer-mode DOM i wymaga
  jawnego przejścia do `Audyt techniczny`.
- Read-only refresh `wordpress_sklep` i Ahrefs z 2026-07-16 przywrócił
  freshness. Oba canonical `vendor_read` zakończyły się po 2 dowody, z
  zewnętrznym odczytem i zapisem metryk, bez błędów lub brakujących
  credentials. Snapshot zwraca `fresh` i puste stale/missing/blocked connector
  lists. Kolejka pozostaje uczciwie `blocked`: 2 kandydatów, 1 actionable,
  minimum 3. Nie wolno wymyślać trzeciego tematu.
- Service Profile dla wybranego work itemu jest związany z usługą, ale jego
  publiczne karty nadal wymagają review; WILQ nie przedstawia tego jako
  zatwierdzonej polityki twierdzeń.
- Zapisane wersje są append-only i wracają po reloadzie. Niezapisane edycje są
  wyłącznie lokalnym stanem formularza. Review dotyczy dokładnego
  `revision_id`, digestu treści i digestu paczki planu; zmiana kontekstu
  unieważnia review. WordPress handoff/apply jest revision-bound i wysyła body
  immutable rewizji. `dev_draft` prowadzi ten sam binding przez cały inline
  ActionObject chain i po sukcesie odświeża snapshot, readiness i readback.
  Obecny dowód jest syntetyczny; nie wykonano realnego write do WordPressa.
- Nawigacja nie wywołuje write requestów. Preview pozostaje dry-run, a każdy
  przyszły zapis WordPress musi przejść przez exact ActionObject, confirmation i
  audit; publish/update/delete pozostają poza tym journey.
- Bieżąca prawda pozostałych tras jest w `docs/dashboard-state.md`, stan
  bieżącego slice’a w `docs/PROGRESS.md`, a graf pracy w Beads. Nie duplikuj
  tutaj zamkniętych seamów ani historycznych screenshotów.

## Granica bezpieczeństwa

- Requestowe `reviewed_by`, `confirmed_by` i `checked_by` nie nadają
  autorytetu. Action audit używa `local_operator` / `ekologus_local_pilot` /
  `local_unverified`, a przesłany tekst zachowuje tylko jako etykietę. Planning
  i revision review pokazują ten sam server-owned principal/trust obok
  historycznego reviewer label. Nie claimuj owner/expert acceptance ani auth.
- Kanoniczne `.local-lab/runtime` i `.local-lab/state` są normalizowane do
  `0700`, a PID-y, logi, SQLite i DuckDB do `0600`. WILQ nie zmienia praw
  istniejącego katalogu nadrzędnego dla niestandardowej ścieżki DB. To chroni
  lokalne artefakty pilota. SQLite/DuckDB mają jawne wersje schematu, a CLI
  backup/restore przyjmuje tylko nowe alternatywne ścieżki i porównuje liczniki
  rewizji, auditów i metryk. Jest syntetyczny recovery proof; realna migracja i
  restore drill nadal wymagają maintenance window.
- Content router zawsze przekazuje `create_draft=None` i
  `action_apply_authorized=False`.
- Direct live zwraca `action_apply_required` przed adapterem.
- Readiness: `ready=false`,
  `write_authorization_status=blocked_outside_action_apply`, suggested `null`.
- Central mutation summary: 0 vendor-write possible i 0 attempted.
- React ma wyłącznie builder `mode=dry_run`, `write_authorization=null`; UI nie
  utrwala już niemożliwego direct live contractu.
- Existing draft jest otwierany/podglądany; brak create/duplicate CTA.
- Create/apply akceptuje wyłącznie aktualny approved revision binding i
  najnowszy uporządkowany ślad preview/review/confirm/impact z tym samym
  bindingiem. Atomowy claim serializuje apply z append/re-review; drugi request
  i replay starej zgody kończą się przed adapterem. Legacy eventy są czytelne,
  ale nie autoryzują adaptera. Dashboard przekazuje exact binding we wszystkich
  binding-capable requestach i nie ponawia apply po typed `409`; nowszy binding
  resetuje lokalne akceptacje. Publish, update i delete pozostają poza zakresem.
- Claim zapisuje `action_apply_started` przed vendor call. Outcome, mutation
  audit i execution/post ID są finalizowane w jednej transakcji. Po crashu
  lokalne `wilq wordpress-apply reconcile` czeka 300 sekund, wymaga jawnej
  inspekcji, sprawdza status draft dla `applied` i nie ponawia vendor write.

## Bieżący graf

- Techniczne epiki `wilq-seo-c9h9`, `wilq-seo-3bst` i `wilq-seo-amj2` są
  zamknięte odpowiednio z 43/43, 28/28 i 10/10 zamkniętymi dziećmi. Aktywny
  produktowy goal to `wilq-seo-1oa`; jego realne bramki to reviewed knowledge
  (`lt1`) i Wilku UAT (`jst`). `v9ab` pozostaje otwarty przez review `v9ab.13`.
- Fixed-point `wilq-seo-c9h9.26` rozdzielił pracę od historycznych ticketów.
  `wilq-seo-jnra`, `wilq-seo-djly` i `wilq-seo-kgvy` są zamknięte po świeżych
  testach parity, Ruff/mypy i live proof z 21 akcjami oraz 0 możliwych vendor
  writes. Nie wracaj do mechanicznego splitu bez nowego błędu lub kosztu
  produktu.
- Canonical production-pilot graph jest w `wilq-seo-amj2`. Jego pierwsze dwa
  P0 to prawdziwa readiness kroku `dev_draft` (`amj2.2`, domknięta) oraz
  persisted review scope/section map (`amj2.1`). Backend/store tego review jest
  domknięty w `amj2.1.1`, formularze/reload/conflict i browser proof w
  `amj2.1.2`, a downstream planning binding w `amj2.1.3`.
  Snapshot wiąże
  `dev_draft.can_submit` z istniejącym exact revision-bound handoffem; brak
  rewizji lub zmiana kontekstu pozostają zablokowane. Typed demand evidence
  (`amj2.3`) i zgodny content skill (`amj2.4`) są domknięte; oba używają tych
  samych decyzji planistycznych i exact dev readiness.
- Lokalna granica pilota `.5`–`.8` ma loopback-only, server-owned identity,
  private filesystem modes i syntetyczny versioned recovery proof.
  `amj2.9` domknął publication-bound measurement: exact WordPress post/URL musi
  wrócić jako `publish`, a okresy, metryki i wynik ładuje serwer. Klient podaje
  tylko `work_item_id`. `amj2.10` dodaje trwały review-only learning proposal z
  zamkniętego outcome; literalne flagi blokują zmianę wiedzy, kolejki i success
  claim bez osobnej akceptacji.
- `wilq-seo-c9h9.27` jest domknięty: connector i system status współdzielą
  typed lokalną gotowość CLI/login, nie wymagają `CODEX_API_KEY`, nie czytają
  loginu i nie ujawniają jego ścieżki. Live status jest `configured`; brak CLI
  i brak sesji pozostają osobnymi bezpiecznymi stanami.

- `wilq-seo-r564.7` jest zamknięty i wypchnięty w `b23e413a`.
- `wilq-seo-r564.8` jest zamknięty: append-only draft revisions i human
  decisions są związane z dokładną wersją i digestami.
- `wilq-seo-r564.9` jest zweryfikowany: exact revision handoff, ActionObject i
  draft-only adapter używają jednej wersji; legacy/v2/tamper są fail-closed.
- `wilq-seo-r564.10` jest zweryfikowany: inline wizard utrzymuje ten binding od
  preview do apply, wznawia wyłącznie zgodny ordered audit i zatrzymuje typed
  konflikt bez retry. Desktop/mobile proof jest syntetyczny i nie dotyka
  WordPressa.
- `wilq-seo-r564.11` jest zamknięty i zweryfikowany: full grounded input przechodzi przez
  lokalny app-server, obcy lineage jest fail-closed, a poprawny wynik tworzy
  niezatwierdzoną child revision z run/evidence/claim trace. Realny output ma
  verdict `needs_changes`, więc usefulness tworzenia treści pozostaje 5/10.
- `wilq-seo-r564.12` jest zamknięty: zwalidowany
  `normalized_page_path` zachowuje exact publiczną ścieżkę w context-packu,
  natomiast tokenowe, sekretowe i malformed ścieżki pozostają redagowane.
- `wilq-seo-r564.13` jest zweryfikowany: marketer wybiera exact sekcje i widzi
  pending/diff/findings bez promptu w browserze, approval ani WordPress write.
  Cross-work-item result i brak wybranej sekcji są fail-closed. Proof 1440×900 i
  390×844: `.local-lab/proof/dashboard-content-workflow/2026-07-15T19-06-55-670Z/`.
- `wilq-seo-r564.14` jest zweryfikowany jako cleanup dawnej równoległej ścieżki:
  po nim wszystkie późniejsze content-model POST-y nadal korzystają z jednego
  server-side app-servera; internal generation contract nie jest martwym
  artefaktem.
- Parent `wilq-seo-r564` jest zamknięty: wszystkie 14 dzieci są closed, świeży
  dashboard gate przechodzi 164/164, a live snapshot zachowuje konkretny item,
  evidence, Service Profile review gate i `publish_ready=false`. Queue density,
  owner-reviewed Service Profile i Wilku UAT pozostają otwarte poza tym bounded
  workbench outcome; stale sklep/Ahrefs zostało usunięte read-only refreshem.
- Nie kopiuj tutaj pełnej listy Beads ani historii zamkniętych seamów. Po każdym
  pushu odczytaj `bd ready --json` i `bd list --status=open --json`.

## Verification checkpoint

- Fresh parent proof `r564`: 14/14 dzieci closed, dashboard 164/164, API health
  200, `/content-workflow` 200. Exact homepage snapshot agreguje 29 bieżących
  sygnałów planistycznych GSC do 47 wyświetleń i 3 kliknięć; cztery najwyższe
  wiersze są widoczne bez udawania mapowania sekcji. Karta kontekstu i panel
  planowania korzystają z tego samego snapshotu. Krok pozostaje `scope`,
  Service Profile `source_backed_review_required`, `publish_ready=false`.
  Follow-up snapshot po canonical refreshach sklepu i Ahrefs ma `fresh`,
  `requires_refresh=false` i puste stale/missing/blocked connector lists.
- Content state proof nie zamraża już dokładnego zdania CTA. Nadal sprawdza
  review gate, brak draft/publish readiness oraz knowledge-card lineage; focused
  repro po usunięciu redundantnej asercji jest zielony 1/1.
- Loopback proof jest zielony 14/14. Kanoniczny test używa ASGI peer scope:
  remote peer ze spoofed local Host dostaje `403`, a loopback peer z malicious
  Host dostaje `200`. Usunięto tylko sprzeczny test Host-header; middleware bez
  zmian.
- Review-only learning proof jest zielony: brak outcome i `insufficient_data`
  zwracają `409`, caller-supplied acceptance zwraca `422`, a zamknięty wynik
  tworzy trwały proposal z pełnym publication/metric lineage i wszystkimi
  mutation flags `false`. Zamknięcie window i outcome zapisują się atomowo.
- Publication-bound measurement proof jest zielony 5/5: przed exact publish
  nie ma okna, obie próby podania client-owned okresu/wartości zwracają `422`,
  snapshot bez porównywalnego okresu albo z dodatkowym segmentem daje
  `insufficient_data`, a dopiero syntetyczny WordPress publish i okresowe
  page-aggregate fakty GSC pozwalają serwerowi utrwalić okno i wyliczyć
  `measured_success`. Exact-URL query oraz okres raportu GA4 są częścią
  provenance. Ruff i mypy są zielone. Realnego store/runtime nie
  migrowano ani nie restartowano bez maintenance window.
- Focused proposal/store/preview chronią pełny grounded input, body-only claim
  leakage, brak quality credit z model-only delivery fields, atomowość child
  revision z CodexRun i fail-closed tool attempt; 29/29 przechodzi. Focused
  redaction przechodzi 5/5, a pierwotny context-pack repro 1/1.
- Browser proof proposal: exact needs-changes base → wybór sekcji → pending →
  baza/child → findings → semantic review, 1440×900 i 390×844, bez overflow i
  bez requestu WordPress. Proof:
  `.local-lab/proof/dashboard-content-workflow/2026-07-15T19-06-55-670Z/`.
- Osobny browser proof handoff: save → refetch/reload → exact review → preview → review akcji
  → confirm → impact → syntetyczny apply → draft-only readback, 1440×900 i
  390×844. Endpointy ActionObjectu są przechwycone; zero realnego WordPress
  write. Proof:
  `.local-lab/proof/dashboard-content-workflow/2026-07-15T11-50-52-058Z/`.
- Focused API/UI przechodzą 32/32, TypeScript i ESLint są zielone, focused
  Playwright przechodzi 1/1, a niezależny Standards+Spec review nie znalazł
  uchybień. Syntetyczny proof nie zastępuje Wilku UAT.
- Aktualny szeroki `scripts/verify.sh` doszedł do 986 backend testów (2 skip) i
  ujawnił jeden błąd redakcji; po naprawie jego pierwotny publiczny repro jest
  zielony. Umbrella nie był powtarzany dla już zielonych testów. Aktualne
  `security.sh`, Ruff, mypy, oba content skill smokes oraz niezależny
  Standards/Spec/security review są zielone.
- Kanoniczny `local_stack.sh restart` kończy się zdrowym API `:8000` i
  dashboardem `:5173`; health, metrics, content queue i `/content-workflow`
  zwracają 200.
- Pełny verify uruchamiaj przy zatrzymanym managed stacku: dashboard E2E czyta
  aktualny local evidence store, a równoległy API trzyma lock DuckDB.

## Resume

1. GSC, GA4, Ahrefs, Ads, Keyword Planner i inventory używaj tylko, gdy istnieje
   aktualny typed dowód; brak lub stale źródło jest blockerem, nie wymyśloną
   metryką ani wolumenem słowa kluczowego.
2. Ponownie odczytaj Beads i roadmapę; nie wracaj do ukończonych `.9`, `.10`
   ani `or2e` bez nowego repro.
3. Przygotuj review-ready paczkę tekstów; jakości 10/10 nie claimuj przed
   realnym Wilku UAT i owner-reviewed Service Profile.
