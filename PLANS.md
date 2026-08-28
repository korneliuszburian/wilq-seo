# WILQ — ExecPlan: evidence-bound Ekologus content delivery

> Rola: bieżący plan wykonawczy dla jednego długiego celu. Stan procesu i
> claimy o wykonaniu należą do aktywnego Beada oraz zweryfikowanych artefaktów;
> ten plik porządkuje kolejność, zakres i kryteria ukończenia. Nie tworzy
> drugiej kolejki zadań.

## Handoff do nowej instancji SOL (stan na 2026-08-28)

Ten blok jest instrukcją wznowienia, nie osobnym planem. Nowa instancja ma
traktować ten plik, aktywny Bead `wilq-seo-1oa.36.99` i dziennik stanu jako
jedną ścieżkę prawdy. Nie odtwarzać wcześniejszych odczytów tylko po to, by
powtórzyć logi.

### Jedyny cel i rola modeli

- Handoff follows the official long-running-work guidance: define one clear
  outcome, constraints, verification and resumable state; see
  <https://learn.chatgpt.com/docs/long-running-work>.
- Cel: dowieźć evidence-bound treści SEO dla `ekologus.dev.proudsite.pl` —
  wszystkie 214 URL-i rozstrzygnięte, 57 `keep` obsłużonych albo jawnie
  zablokowanych, z exact ACF/`the_content` mappingiem, claim/source lineage,
  QA i bezpiecznym dev-draft workflow.
- SOL jest orchestrator/reviewerem: utrzymuje plan, deleguje bounded slice do
  Luny/Codexa, weryfikuje diff i dowody, prowadzi Bead i zatrzymuje się przy
  blockerze. Luna/Codex jest wykonawcą kodu lub artefaktów, nie właścicielem
  approval, Beads, merge, publikacji ani vendor mutation.
- SOL dobiera effort do ryzyka: Luna dla mechanicznego odczytu i małych,
  odwracalnych zmian; SOL-ULTRA dla architektury, korelacji connectorów,
  security/quality review i decyzji fixed-point. Żaden model wykonawczy nie
  może sam uznać pracy za zaakceptowaną ani rozszerzyć zakresu.
- Delegacja ma być non-interactive i audytowalna (`codex exec --ephemeral` z
  exact worktree, `--json` i retained last-message); SOL po każdym wyniku
  sprawdza `git diff`, focused falsifier i stan Beada. Opinia drugiego sędziego
  jest niezależnym wejściem, nie automatycznym approvalem.
- Każdy slice ma jednego autora, jeden observable result, focused falsifier,
  semantic commit i external fixed-diff review. Nie scalać mikrofixów w
  bezładny batch i nie uruchamiać równoległych writerów na tym samym checkout.

### Gate przed nową pracą

PR #20 (service binding) został scalony jako merge commit
`4ebedbf04ff424256d7e830b4326b0fda9299c15`, z rodzicami exact base
`cac3036d514437dbbeeec8f207a5b341749b5872` i zaakceptowanym headem
`e1c86af207a16c11a39d3791e5dd7a8b5492ec87`. Post-merge Quality
`33188000685` zakończył wszystkie trzy joby sukcesem. Exact URL binding,
provenance i fail-closed ambiguity/staleness są więc częścią `origin/main`;
wcześniejsze fuzzy sygnały nadal nie są bindingiem usługi ani claimu.

### Fakty, których nie wolno zgubić

- Dev sitemap: 214 unikalnych ścieżek; canonical robot manifest: 214 rekordów
  (`57 keep / 87 noindex / 46 redirect / 24 remove`) i exact set equality.
- REST dev: 175 obiektów (`115 posts / 8 pages / 52 uslugi`); 57/57 `keep`
  ma obiekt. Współistnieją trzy role: 137 publicznych SEO inventory, 175
  obserwacji REST i 214 dev/site-map decision inventory. Nie dodawać hosta dev
  do publicznego katalogu SEO.
- ACF snapshot: 58 niepustych flexible surfaces, 116 `the_content`, 1 pusty
  root; `keep` to 45 post-content, 1 page-content, 4 page-ACF i 7 uslugi-ACF.
  To obserwacja, nie pełne writable mapping/readback.
- Offline `dev_authoring_inventory` projektuje dokładnie 214 targetów z tych
  snapshotów: 175 obserwowanych obiektów REST i 39 jawnych braków obserwacji;
  wszystkie 57 `keep` ma obiekt. Artefakt pozostaje observation-only, bez
  mapowania zapisu i bez zmiany publicznego katalogu SEO.
- Source packs: 181/181 sprawdzone po SHA/size w jawnie zapisanym retained root;
  dev→public host alias i path-only join są jawne. Nie czytać prywatnego packetu.
- WILQ API (read-only snapshot): 12 connectorów, 9 skonfigurowanych, 2 brakujące
  credentials; GSC/GA4/Ahrefs/Ads/WP evidence IDs istnieją, Keyword Planner
  pozostaje `blocked`; `ready_for_daily_content=false`, mutation/write false.
- Candidate bundle: 57 plików, 16 753 słów; 43/57 poniżej 300 słów. Wszystkie
  `publish_allowed=false`, `write_authorized=false`, `robot_ready=false`.
- Dev-state journal: jeden indeks 214 URL-i, znane drafty, mutation audits,
  action-binding recovery i referencje do sitemap/ACF/canonical/source/audit.
  Preflight: `eligible=0`; nie generować kolejnego draftu dla URL/revision/action
  już zarejestrowanego.

### Kolejność po wznowieniu

1. Odczytać `bd show wilq-seo-1oa.36.99`, ten blok, journal i aktualny main/CI.
2. Używać wyłącznie scalonego exact service bindingu z PR #20; nie wracać do
   fuzzy auto-bindingu ani do wcześniejszych headów.
3. Traktować `dev_authoring_inventory` jako zamkniętą observation-only
   projekcję 214/175/39; nie tworzyć drugiego inventory ani nie rozszerzać
   publicznego SEO catalogu.
4. Dla każdego `keep` rozwiązać exact work-item → service card → source pack →
   revision → target contract. Fuzzy/GSC/Ahrefs są sygnałem/kandydatem, nigdy
   samodzielnym bindingiem. Brak któregoś elementu = typed blocker.
5. Dopiero dla eligible rows uruchamiać planner → writer → critic/repair na
   jednym canonical document, następnie local QA/global dedupe/link graph i
   draft-only ActionObject preview. Żadnego vendor write bez odrębnej zgody.
6. Na końcu zbudować jeden graph 214 URL-i z działającymi tylko zweryfikowanymi
   krawędziami oraz raport `ready / needs_review / blocked`; nie deklarować
   production readiness, UAT ani publikacji bez dowodu.

### Kryterium zatrzymania / wznowienia

Zatrzymać jako `BLOCKED`, gdy brakuje świeżego evidence, owner review, exact
service/target mappingu, credentials albo osobnej autoryzacji zapisu. Nową
instancję wznowić od ostatniego Bead comment i hashy artefaktów; nie tworzyć
drugiego goalu, drugiego journalu, kolejnego manifestu ani „tymczasowego”
endpointu. Wszystkie commity muszą być semantic i ograniczone do jednego
cohesive slice.

## Outcome

Dowieźć dla `ekologus.dev.proudsite.pl` audytowalny pakiet treści SEO:

- 214 URL-i z decyzją `keep/noindex/redirect/remove` i canonical/duplicate
  lineage;
- treść wyłącznie dla 57 URL-i `keep`, z page assets, sekcjami, FAQ, CTA,
  linkami i sentence-level claim ledgerem;
- source-packi oraz GSC, GA4, Ahrefs i Ads z zachowanym evidence lineage;
- exact WordPress `the_content`/ACF target mapping, preview i readback contract;
- robot manifest, który ustawia `robot_ready=true` tylko po przejściu wszystkich
  bramek. Keyword Planner pozostaje `blocked` bez zmyślania.

## Constraints

- Nie generować ani nie mapować treści dla `noindex`, `redirect` lub `remove`.
- Nie zgadywać usługi po slugu, nie promować niezatwierdzonych Service Profile
  cards i nie tworzyć rewizji bez exact work-itemu, źródeł i aktualnego
  kontekstu.
- Każdy claim, CTA, link, metryka i asset musi mieć identyfikowalne źródło oraz
  freshness; kontekst batchowy nie jest dowodem page performance.
- Nie czytać ani nie utrwalać `.env` lub prywatnego packetu; nie wykonywać
  WordPress/vendor write, ActionObject apply, deploymentu ani live mutation.
- ACF wymaga pełnego, zatwierdzonego mapowania komponent → pole; częściowe
  observed fields nie są zapisem.
- Po ekstrakcji używamy snapshotu i `docs/content-dev-state-journal-20260828.json`;
  nie odpytywać ponownie per URL tylko po to, by odtworzyć już zapisany dowód.
  Nowy odczyt jest uzasadniony wyłącznie zmianą źródła, wygaśnięciem freshness
  albo brakującą tożsamością, a wynik zawsze dostaje nowy timestamp i hash.
- Beads jest właścicielem stanu pracy, a archiwalny graph/audit jest dowodem
  artefaktów. Nie tworzyć równoległego TODO ani drugiego celu.

## Verification contract

Ukończenie wymaga aktualnych dowodów dla każdego wiersza, nie samego istnienia
pliku:

1. canonical manifest ma dokładnie `214 = 57/87/46/24` i każdy disposition ma
   evidence/canonical lineage;
2. wszystkie 57 keep URL-i mają unikalne page assets, source/claim coverage,
   zweryfikowane CTA/link destinations i brak niedozwolonej duplikacji;
3. każda bieżąca rewizja przechodzi schema, semantic/formal review oraz exact
   target mapping/readback; ACF nie może zostać częściowo zapisany;
4. robot manifest pokazuje prawdziwy stan per URL; `publish_allowed` i
   `write_authorized` pozostają false do osobnej autoryzacji;
5. końcowy proof obejmuje counts, SHA, link resolution, connector freshness,
   `git diff --check` i odpowiednie focused/broad gates.

## Execution stages

| Stage | Result | Current evidence |
|---|---|---|
| 0. Inventory, connector context and source-pack lineage | complete with external-root caveat | 181 pack refs verified 181/181 by SHA/size at the retained final source-pack root; public dev sitemap 214 unique paths exactly covers the manifest; GSC/GA4/Ahrefs/Ads/WP evidence IDs; Keyword Planner blocked |
| 1. Canonical and duplicate decisions | complete | 214 rows: 57 keep, 87 noindex, 46 redirect, 24 remove; explicit targets/receipts are sealed in the canonical ledger |
| 2. Candidate delivery and page-asset projection | complete as candidate-only | 57 Markdown candidates; 9 historical projection rows + 48 rebase candidates; no write/apply authority |
| 3. Current revision/service binding | in progress | Exact-only service binding is merged in `4ebedbf0`; 13 current approved revisions exist, while 44 candidate rows remain typed-blocked (`28` no work-item + `15` blocked + `1` stale) and one planning `read_error` belongs to an existing verified draft; next result is one per-keep eligibility/blocker projection, never heuristic promotion |
| 4. ACF/the_content mapping and readback | in progress | Read-only REST inventory covers all 175 content objects (58 non-empty ACF surfaces, 116 `the_content` surfaces, 1 empty ACF root; 57/57 keep paths matched); full component write mappings and readback authority remain 0 |
| 5. Final robot-ready gate | pending | stays `robot_ready=0` until stages 3–4 and owner/legal review pass |

## Current authority and recovery links

- Active Bead: `wilq-seo-1oa.36.99` (the only implementation WIP).
- [Current delivery graph](</mnt/storage/krn/archive/wilq-content-run-raw-20260826/new-design-content-handoff-graph-20260828.md>) — visual map, artifact index and hashes.
- [Completion audit](</mnt/storage/krn/archive/wilq-content-run-raw-20260826/content-completion-audit-v2-20260828.json>) — requirement matrix and blockers.
- [Robot manifest](</mnt/storage/krn/archive/wilq-content-run-raw-20260826/content-robot-manifest-20260828.jsonl>) — per-URL delivery authority.
- [Canonical ledger](./docs/content-canonical-ledger-20260828.jsonl) — 214-row sanitised projection with explicit canonical/redirect targets and 46/46 redirect receipts (SHA256 `b62a45476a51768c829b5878a934c013e2c5f0b852780f2ec4498c3b3feb5506`; summary `b5efa063a3daf1b8b09e7fb1b4152e5fdb5c815a4772d15d11243e25616856b4`).
- [Source-pack verification](./docs/content-source-pack-verification-20260828.json) — explicit retained final root and 181/181 SHA/size proof; declared dev→public host alias plus trailing-slash path join; archive-relative paths alone are intentionally marked non-resolving (SHA256 `ef9d961e8c7935666aa35708d471a98f64ecb1cce4de81807f812f51d47f94dc`).
- [Candidate quality audit](./docs/content-candidate-quality-audit-20260828.json) — read-only checks over all 57 candidate files: 57/57 present, one H1 each, zero AI-placeholder tokens and exact duplicate paragraphs, but 43/57 are under 300 words and all remain candidate-only (SHA256 `b244a08e1cf410952a5ce99a2ffeede00c9bd5cf49b1c29560cc4864e95d4a4a`).
- [Current ACF observation](</mnt/storage/krn/archive/wilq-content-run-raw-20260826/acf-mapping-current-observation-20260828.json>) — exact `OPTIONS` profiles and observed writable fields; no raw values.
- [Public sitemap inventory](./docs/content-sitemap-inventory-20260828.json) — read-only dev/old URL topology; 214 unique dev paths match the manifest exactly, old-domain comparison excludes product sitemaps and is not a content authority (SHA256 `0f0cd730f6b480b284da7be6631dfc4b22a0a645c4582abfe209367d82590c0c`).
- [Public ACF inventory](./docs/content-acf-inventory-20260828.json) — one read-only REST snapshot of 175 `posts/pages/uslugi` objects; ACF field/layout names and digests only, no body or raw values. All 57 keep paths have an exact object; 46 use `the_content` and 11 use non-empty ACF layouts. This is observation, not write mapping (SHA256 `97281a48774c1893d80c235555074d9c7502d68074479c7b59795357a64e1a80`).
- [Dev authoring inventory](./docs/content-dev-authoring-inventory-20260828.json) — deterministic offline projection with `inventory_role=authoring_target`, 214 sitemap observations, 175 exact REST identities and 39 explicit `rest_object_not_observed` blockers; all publication/write/generation/robot gates remain false (SHA256 `6f1a381901cdeec7e2d5215e12305087018330c3854830770908a79ebae122ec`).
- [Dev state journal](./docs/content-dev-state-journal-20260828.json) — one read-only index of URL state, every known dev draft and content mutation audit; consult it before any new generation.
- [Action binding recovery](./docs/dev-content-action-binding-recovery-20260828.json) — seven historical ActionObject bindings recovered from API metadata; vendor post IDs remain explicitly unknown.

Current integration fixed point is branch `agent/content-delivery-integrated`
over merged main `4ebedbf0`; it replays the handoff and reviewed inventory
without changing their retained artifact bytes. Publication/content/vendor
authority remains false despite repository lifecycle authorization.

The next executable action is one read-only per-keep eligibility/blocker
projection over the integrated exact binding and authoring inventory. It must
re-read the Bead, journal and preflight first, preserve `eligible=0` unless every
required lineage gate actually closes, and never regenerate an indexed
URL/revision/action. The sitemap inventory proves URL topology only; it does
not grant source approval, ACF mapping or WordPress write authority.

---

## Historical context (not the current execution plan)

> Rola: historyczny kontekst produktu. Nie zastępuje `AGENTS.md`, aktywnego
> Beada ani nazwanego rekordu bieżącego stanu. Sformułowania „aktywny” i
> „bieżący” poniżej opisują moment powstania dokumentu, nie obecny workflow.

Ten plik zachowuje wcześniejszy standard i kierunek produktu; nie jest aktualnym
planem wykonawczym ani równoległą kolejką zadań.

### Aktywny execution goal — production-ready Treści i SEO (2026-07-20)

Najbliższy rezultat nie jest kolejnym proof-of-conceptem: `/content-workflow`
ma wyglądać i działać jak gotowe narzędzie pracy marketera. Za wizualny fixed
point przyjmujemy dostarczone makiety desktop/mobile: kompaktowy hero strony i
usługi, jeden dominujący next step, realne metryki, grupy Faktów/Sygnałów/Blokad,
wnioski z powodami, poziomy workflow oraz page-like tekst i review.

Definition of Done dla tej powierzchni:

1. **Wybór**: dowolna strona z kolejki lub pełnego inventory WordPressa, jawnie
   dobrana usługa, rozpoznanie ACF albo `the_content` bez ręcznej mapy sekcji;
   BDO jest tylko przykładem, nigdy domyślnym ograniczeniem produktu.
2. **Brief/plan**: jeden aktualny plan z query assignments, page assets, FAQ,
   CTA, linkowaniem i źródłami; marketer widzi decyzję, wpływ, freshness i
   blocker, a szczegóły techniczne są progressive disclosure.
3. **Tekst**: pełny dokument w układzie strony, stabilne section IDs, meta/H1/
   lead/FAQ/CTA/linki oraz lineage do zatwierdzonych materiałów i evidence.
4. **Review**: deterministyczne bramki i persistowany advisory semantic review
   są widoczne jako pomoc, ale tylko człowiek zatwierdza exact revision.
5. **Dev preview**: tylko revision-bound WordPress draft preview/action; brak
   publikacji, brak bezpośredniego vendor write, brak auto-approval.
6. **Responsive UX**: desktop i mobile mają tę samą hierarchię; pierwszy
   viewport odpowiada w około 30 sekund: co widzimy, dlaczego teraz, co jest
   zablokowane i jaki jest następny krok.

Standard wykonania zgodny z aktualnym Codex manualem: każdy slice ma Goal,
Context, Constraints i Done-when; zmieniamy najmniejszy pionowy fragment,
wybieramy focused falsifier przed testem, zapisujemy checkpoint w Beads/state,
oglądamy live browser proof i dopiero wtedy commit/push. Długie zadanie jest
resumable: context-pack WILQ odświeżany przed decyzjami, brak ponownego
odtwarzania zielonych drogich testów, brak claimu completion bez rendered proof.
Second opinion pozostaje jednym bounded checkerem na fixed point, nie approvalem.

Aktualny fixed point wizualny: `6136024a`; pierwszy viewport ma już disclosure
kolejki, karty realnych metryk i pojedynczy freshness banner. Następny slice
dotyczy production-ready widoków Plan/Tekst/Review/Dev preview zgodnych z tym
samym językiem i hierarchią.

### Checkpoint 2026-07-19 — fixed point po browser-proof `/content-workflow`

Ostatni utrwalony stan obejmuje serię runtime i lineage hardening slices. `GET /initial-draft` nie
pokazuje już starej rewizji jako aktualnej po nowszym planning jobie z innym
digestem; zwraca typed `stale_planning_input` bez model call. Measurement
aggregator scala powtórzone exclusions per `code/source/metric/period`,
zachowując pełną union evidence IDs. Świeży WILQ API context: 12 konektorów,
9 skonfigurowanych, 2 brakujące credentials; brief ma 1 blocker, 3
rekomendacje i 17 evidence IDs; kolejka ma 54 kandydatów, z czego 53 są
actionable. Exact BDO readback ma 35 faktów i 4 wykluczenia `wrong_period`.
Oba piloty planowania nadal kończą się typed `runtime_failed` z
`codex_response_stream_disconnected`; queued digest, terminalny `CodexRun.id`
i persisted readback są zachowane;
pełna generacja, semantic storage, jakość tekstu i UAT pozostają nieudowodnione.

Ostatni wypchnięty commit: `e615205d` (`perf(runtime): keep daily brief warm for marketer sessions`).
Po zmierzonym cold-starcie `/api/marketing/brief` (4,056 s) i kolejki (2,820 s)
po wygaśnięciu 30-sekundowego cache domyślny TTL read-only daily runtime wynosi
300 s. Env override i jawne connector freshness pozostają bez zmian; focused
cache contract i Ruff przechodzą. To nie jest dowód produkcyjnej wydajności ani
UAT.
Pełny `apps/dashboard/e2e/content-workflow-layout.spec.ts` przechodzi 6/6 w
jednym przebiegu; obejmuje desktop/mobile, inventory-bound workflow, planning,
Codex section rewrite oraz save → reload → exact review → draft-only wizard.
To synthetic proof, nie UAT ani zgoda na vendor write. Selektory testu zostały
związane z aktualnymi etykietami UI i payloadem `selected_section_headings`;
produkcja nie została zmieniona w tym slice.

Poprzedni wypchnięty commit: `c4780e8b` (`docs(plan): refresh long-running fixed point`).
Po tym punkcie social reuse zachowuje osobne `source_evidence_ids` historii
duplikacji w immutable proposal i blokuje reuse bez zatwierdzonego inventory;
live social history nadal jest `missing`. Audyt Ads obejrzał wszystkie 21
skryptów: każdy ma realnego callera i odrębne ryzyko kontraktowe, więc nie ma
udowodnionej bezpiecznej kasacji ani mechanicznego merge'u. Deterministyczny
Ads smoke nadal przechodzi na żywym API (6 walidacji akcji, 16 sekcji, 14
decyzji, 7 kart wiedzy). Bead pozostaje jawnie `in_progress`, dopóki nie
pojawi się konkretny caller diff uzasadniający redukcję powierzchni.

Poprzedni stan po `b266f65b` (`chore(beads): record run input binding`) został
zachowany w historii git; nie nadpisujemy go ani nie udajemy, że transport
Codexa, pełna generacja, semantic storage lub UAT są zamknięte.
Po poprzednim pomiarze doszły wspólny kontrakt deadline/stale job oraz izolacja
starych planning jobs po `service_card_id`: nowszy run innej usługi nie może już
unieważnić aktualnego proposal/draft statusu. Transport Codexa klasyfikuje
bezpiecznie stream disconnect ze stderr bez utrwalania payloadu. Niezależne review passy i dispositions
znajdują się poza repo w katalogu second-opinion-review; findings bez źródła
są klasyfikowane jako evidence gaps/reject, nigdy jako PASS.

## 1. Cel i granica produktu

WILQ jest API-first Marketing Operating System dla Ekologus. Ma pomagać
marketerowi analizować dane, wybierać decyzję, tworzyć i poprawiać treści,
przygotowywać kampanie oraz bezpiecznie przekazywać działania do sprawdzenia.
Dashboard i umiejętności Codexa są klientami jednego WILQ API. Nie tworzymy
konkurencyjnych plannerów, drugiego magazynu prawdy ani browser-to-model.

Główny rezultat dla marketera: z realnych danych i zatwierdzonych materiałów
powstaje zrozumiała decyzja, plan, tekst/page assets, review i bezpieczny
WordPress draft. Wartość jest ważniejsza niż liczba ekranów, score'ów i testów.

## 2. Standardy niepodlegające negocjacji

- Każdy fakt, query, claim, CTA, link i metryka ma źródło, identyfikator,
  freshness i lineage. Brak lub starość dowodu daje jawny blocker.
- Nie zgadujemy wolumenu, intencji, wyników, przewagi konkurencji, konwersji
  ani jakości. GSC nie jest kompletnym zbiorem zapytań.
- Surowe prywatne materiały, tokeny, dumpy vendorów i teksty z credentials nie
  trafiają do promptów, logów, paczek ani repo. Do modelu trafiają tylko
  zatwierdzone, zredagowane fakty z lineage.
- Człowiek zatwierdza service scope, claims, exact revision i ActionObject.
  Codex proponuje; nie zatwierdza, nie publikuje i nie wykonuje vendor write.
- WordPress pozostaje draft-only. Każdy write przechodzi przez exact revision,
  preview, human confirmation, safety checks i audit. Brak replayu starej zgody.
- Używamy istniejącego serwerowego Codex app-server i lokalnego logowania.
  Nie dodajemy API keya, Agents/SDK drugiej ścieżki, Ollamy ani bezpośredniego
  wywołania modelu z przeglądarki.
- Nie pokazujemy marketerowi technicznych etykiet jako treści produktu:
  `operator_local_dashboard`, „audyt”, „evidence” i digesty są szczegółem
  „Dlaczego”, a nie nagłówkiem. UI jest po polsku i używa języka decyzji.
- Nie używamy magicznego SEO/content score jako KPI. Deterministyczne bramki,
  advisory review i realna ocena SEO/content/marketera są rozdzielone.
- Zachowujemy istniejące dirty work i historię. Destrukcyjne czyszczenie,
  publikacja, credentials, deploy i push są osobną autoryzacją.

## 3. Doświadczenie marketera (docelowe 10/10)

Pierwszy ekran w około 30 sekund odpowiada: co widzimy, dlaczego teraz, jaki
jest wpływ, czego brakuje i jaki jest jeden następny krok. Marketer może
wybrać każdą dostępną stronę, usługę, artykuł i sekcję — nic nie jest
preselected BDO ani ograniczone do dwóch pilotów.

Kanoniczne kroki:

1. **Wybór** — strona/usługa/sekcja, cel, zakres i jawne potwierdzenie.
2. **Sygnały** — realne metryki, zapytania, źródła, świeżość i decyzja.
3. **Plan** — mapa sekcji, pytania czytelnika, claims, CTA, linkowanie i
   przypisania query/evidence.
4. **Tekst** — pełny page-like dokument: title, H1, lead, body, FAQ, CTA,
   meta i linki; można poprawić wybrane sekcje.
5. **Review i przekazanie** — findings, diff, exact revision, WP dry-run,
   human acceptance i dopiero potem ActionObject draft-only.

Na każdym kroku widoczne są: nazwa strony/usługi, etap, status, decyzja,
metryki i następny krok. Szczegóły lineage są rozwijane w „Dlaczego”. Reload
nie gubi stanu; mobile i desktop mają osobny browser proof.

## 4. Wydajność i zachowanie startu workflow

„Run workflow” nie może wyglądać jak zawieszona strona. Po wyborze dowolnego
elementu:

- pierwszy użyteczny widok (nazwa, decyzja, podstawowe metryki i blocker)
  pojawia się w maksymalnie kilku sekundach na ciepłym lokalnym stacku;
- queue i minimalny snapshot są priorytetem; katalog, authoring profile,
  activation packet, enrichment i ciężkie readbacki ładują się niezależnie,
  lazy albo po otwarciu właściwego kroku;
- żaden GET nie uruchamia Codexa, nie zapisuje propozycji i nie wykonuje
  vendora; błędy pobocznych odczytów nie blokują pierwszego ekranu;
- POST generowania planu zapisuje exact queued job i zwraca `generating`, a
  ciężki snapshot/Codex działa w tle po stronie API; GET tylko odczytuje stan
  i odpytuje go bez ponownego wywołania modelu;
- identyczny digest jest idempotentny, a znany konflikt digestu wraca jako
  `409 stale_input` przed uruchomieniem modelu;
- loading ma mieć osobne stany per panel, timeout i bezpieczny retry, bez
  10-minutowego spinnera. Mierzymy czas każdego endpointu w browser proof.
  Generowanie planu ma osobny bounded Codex deadline (domyślnie 120 s), niezależny
  od draftu i semantic review; przekroczenie zapisuje typed failure bez
  częściowego planu i zostawia retry.
- inventory WordPress może mieć wyłącznie krótki, read-only cache z jawnym TTL;
  daty odczytu, evidence IDs i status freshness pozostają widoczne, a materiał
  i propozycje nie są ukrywane za tym cache.
- optymalizujemy istniejące API seams (cache z poprawną freshness, selektywny
  payload, równoległe read-only calls), nie dodajemy drugiej ścieżki danych.

Wybrany adres jest interakcją priorytetową: queue może użyć katalogu i zwrócić
„materiał wymaga odczytu” bez synchronicznego pobierania pełnego HTML/ACF. Pełny
odczyt pozostaje API-owned, lineage-bound i blokuje plan/draft, jeśli nie da się
go potwierdzić. Katalog jest prewarmowany po gotowości API w tle; prewarm nie
zmienia freshness ani nie jest dowodem kompletności inventory.

Focused falsifier: Playwright wybiera losowy inventory item, klika Run
workflow i sprawdza widoczny decision panel przed zakończeniem secondary
requests; zapisuje czasy i endpointy.

## 5. Dane, źródła i treść

`ContentPlanningInput` jest wersjonowanym, jedynym wejściem planera i zawiera:
work item/canonical URL, kandydatury service cards i powody dopasowania,
potwierdzoną usługę, WordPress inventory, dokładne fakty, freshness,
evidence/knowledge IDs, status każdego konektora (`used`, `not_applicable`,
`missing`, `stale`, `blocked`) oraz digest inputu.

Transport do modelu jest osobną, niemutującą reprezentacją tego kontraktu:
pełny `ContentPlanningInput` pozostaje używany do digestu, walidacji, stale
detection i zapisu; model dostaje wszystkie query rows, ale bez pól `null` i
z ograniczoną powtarzalnością row-level evidence/heading arrays. Top-level
evidence IDs i output schema nadal obejmują pełny dozwolony zbiór.
Kompaktowanie nie może usuwać faktów z API ani zmieniać planning input digestu.
Wersja kryteriów `wilq_people_first_planning_v3` obejmuje także deterministyczną
bramkę odrzucającą nagłówki nawigacyjne, related-content, promocyjne i datowane;
zmiana kryteriów musi unieważnić starsze propozycje przez digest.

Każdy planning fact zachowuje osobno `source_fact_ids` i
`source_material_ids`; samo `evidence_id` lub `knowledge_card_id` nie jest
dowodem pochodzenia wypowiedzi Ekologusa. Materiał bez zaimportowanego,
zredagowanego i zatwierdzonego fragmentu pozostaje review-required i nie może
zasilać publish-ready draftu.
Matcher usług najpierw respektuje exact canonical URL powiązany z lineage
źródłowej karty, dopiero potem szerokie frazy z copy strony; wzmianka o BDO na
stronie outsourcingowej nie może zmienić jej usługi.

Źródła dobieramy kontekstowo: WordPress (realny `the_content`, ACF i struktura),
Service Profile, GSC, GA4, Ads, Ahrefs, Keyword Planner po tokenie, Merchant
tylko produkty, Localo tylko lokalne strony, Social tylko reuse zatwierdzonego
tekstu. Wszystkie dostępne konektory są oceniane, ale do planu trafiają tylko
dokładnie pasujące fakty.

Measurement nie może udawać, że query/detail fact jest już page aggregate.
GSC i GA4 mogą zasilać publication-bound loop dopiero przez server-owned,
exact-URL + exact-period aggregate z zachowaną listą źródeł, refresh runów i
jakością/kompletnością. Wrong period, query variant, ambiguous URL,
capped/insufficient source albo settling data pozostają wykluczone z
allowed/observed metrics z typowanym powodem — bez synthetic targetów i bez
drugiego learning loopu.
Każdy refresh przechowuje dodatkowo typed `covered_window`,
`settlement_state` i `quality_state` wraz z caveatami kompletności/capu.
Semantyka jest własnością konektora: brak sygnału settling oznacza `unknown`,
a nie automatycznie „świeże”; `partial`/`unverified` nie może zasilać
publish-ready ani review-bound obserwacji bez jawnej decyzji kontraktu.

„Knowledge” oznacza prawdziwą bazę materiałów Ekologus: zatwierdzone artykuły,
transkrypcje, dokumenty, wcześniejsze sformułowania i wnioski. Karty i
playbooki są wtórnym, lineage-preserving indeksem; nie zastępują źródeł i nie
mogą zawierać zmyślonych stwierdzeń. Import surowych materiałów jest osobnym,
kontrolowanym krokiem z redakcją, owner review i audytem.

## 6. WordPress/ACF i pełny dokument

Inventory musi dynamicznie wykrywać dla każdej strony: post type, canonical URL,
`the_content`, dostępne ACF, zwykłe pola, sekcje i status odczytu. Brak ACF nie
jest błędem — news/article może być w całości w `the_content`. Renderer i
dry-run zachowują wszystkie page assets, a nie tylko tytuł i nagłówki. Meta
mapujemy automatycznie wyłącznie przy potwierdzonym profilu; inaczej pokazujemy
typed blocker, niczego nie gubiąc.

`ContentDraftRevision` v2 przechowuje title/H1/lead/meta, stabilne section IDs,
body, query/evidence/claim IDs, FAQ, CTA, linki, planning/service/inventory
digests i digest całego dokumentu. Starsze v1 pozostają czytelne. Każda zmiana
assetu unieważnia review i handoff.

## 7. Jakość i review

Trzy niezależne poziomy:

1. deterministyczne gates (lineage, freshness, claims, duplikacja,
   kompletność, długości, linki, CTA, bezpieczeństwo);
2. persistowany advisory semantic review związany z exact revision digest,
   criteria version i Codex run ID;
3. człowiek (SEO reviewer, content editor, marketer), który jako jedyny może
   dać 10/10 i zaakceptować revision.

Review nie poprawia automatycznie własnego tekstu i nie wykonuje vendor write.
Finding wybiera marketer, a Codex zapisuje nową immutable child revision.
Nie przedstawiamy syntetycznego browser proof jako realnego UAT.

### Jeden wynik kanoniczny, nie galeria wersji

Planer i generator mają zwracać jeden rekomendowany wynik dla jednego
`planning_input_digest`. Idempotentne ponowienie tego samego wejścia odczytuje
ten sam proposal albo jego stan generowania; nie tworzy v2, v3 i v10 tylko
dlatego, że marketer ponownie otworzył ekran.

Numery wersji dotyczą wyłącznie trwałości kontraktu i historii rewizji:
`ContentDraftRevision` v1/v2 oznacza schemat odczytu, a numer rewizji oznacza
niezmienny punkt dokumentu. Nie są to alternatywne teksty do wyboru.

Warianty mogą powstać tylko jako mały, wewnętrzny eksperyment jakościowy dla
konkretnego pola lub sekcji (np. dwa leady po findingu dotyczącym bezpośredniości).
Każdy wariant musi mieć te same query/evidence/claim IDs, a marketer dostaje
jedną rekomendację z krótkim uzasadnieniem. Alternatywy nie są zapisywane jako
konkurencyjne propozycje, nie trafiają do głównego UI i nie mogą omijać review.
Domyślna ścieżka nie generuje wariantów. Testy A/B po publikacji należą do
istniejącego publication-bound measurement loopu, nie do planera.

### Standard dla całego Marketing OS

Każdy moduł (treści, GSC, GA4, Ads, Ahrefs, Merchant, Localo, Social i
kampanie) ma ten sam minimalny wynik: decyzja, realne fakty, okres i freshness,
identyfikatory evidence/source, jawne braki, bezpieczny następny krok oraz
granica człowieka. Moduł może pokazywać tylko pola, które ma typed kontrakt;
brak kontraktu jest blokadą, nie miejscem na brainstorm modelu.

Campaign Builder jest obecnie review-only dla istniejących kampanii: może
zwrócić campaign candidates, derived KPIs, landing/context, budget preview,
human gates, missing contracts, blocked claims i ActionObject. Nie udaje
generatora keywords, ad groups, assets, sitelinks, copy, targetowania,
budżetów docelowych ani prognoz. Odczyt wielu walut blokuje sumowanie i
etykietowanie kosztu jedną walutą do czasu potwierdzenia spójności konta.

## 8. Kolejność pracy i dowody

### Natychmiast

1. Zdiagnozować i naprawić opóźnienie Run workflow; focused timing + browser
   falsifier, bez testowania w kółko zielonych ścieżek.
2. Dokończyć marketer-first UI: wszystkie inventory entries, brak preselection,
   mięso nad technicznymi panelami, per-panel loading i czytelne błędy.
3. Zweryfikować aktualny operator context pod istniejącym API; techniczne
   request labels pozostają pod spodem, nie na głównym ekranie.

### Pipeline treści

4. Kontrolowany import zatwierdzonych materiałów: manifest → redakcja →
   owner review → lineage facts → planning input. Bez kopiowania prywatnych
   dumpów.
5. Dokończyć trwały plan i pełny dokument v2, readback, stale detection,
   semantic review, section improvements i draft-only handoff.
6. Użyć dwóch exact pilotów (BDO i doradztwo/outsourcing) jako dowodu jednego
   dynamicznego kontraktu, nie jako hardcoded wyjątków.
7. Zbudować paczkę: decyzja/źródła, baseline, plan, query→section, pełny tekst,
   page preview, meta/FAQ/CTA/linking, findings, dry-run, formularze i realne
   nagranie.

### Cały Marketing OS

8. Po treściach dopiąć jednolite decision views dla Ads, GA4, GSC, Ahrefs,
   Merchant, Localo, Social i campaign buildera; każdy przez istniejący API,
   evidence/freshness i ActionObject safety. Nie powielać measurement loopu.
9. Przygotować non-interactive second-opinion review obejmujący API, dane,
   UX, performance, prompts, security, source lineage, content quality i
   handoff. Każdy finding staje się Beadem lub jest uzasadnionym odrzuconym
   ryzykiem — nie zostaje w raporcie jako dekoracja.

### Przekazanie marketerowi — obowiązujący standard

Robocza paczka przekazania znajduje się w
`docs/review-packets/2026-07-17-wilku-live/`, a jej archiwum w
`docs/review-packets/WILQ-PACZKA-DLA-MICHALA-WILCZKA-2026-07-17-v4.zip`.
Paczka musi rozdzielać dowód live od synthetic/browser proof, podawać datę
odczytu i freshness, identyfikatory evidence/work itemów, jawne blokery,
formularz oceny i instrukcję realnego nagrania. Stare metryki,
`approved_current` bez aktualnego API albo fixture jako „UAT” są
niedopuszczalne. Jeżeli nie ma prawdziwego nagrania, mówimy wprost „nagranie
do wykonania”, nie tworzymy domniemania działania.

## 9. Proof i akceptacja

Każdy slice: claim Beada → najmniejsza zmiana produkcyjna → focused falsifier →
state record/Bead → niezależny review fixed point → świadomy commit/push, jeśli
autoryzowany. Dla zmian TS uruchamiamy wąski typecheck; dla API wąski pytest;
cross-surface `scripts/verify.sh` tylko raz przy szerokim claimie.

Pilot nie jest ukończony, dopóki: obie karty mają owner review; oba case'y
przechodzą ten sam dynamiczny workflow; pełne teksty i assets są trwałe;
brak critical/high findings; SEO reviewer, editor i marketer dają 10/10;
WordPress exact dry-run i human-confirmed ActionObject przechodzą; Wilku UAT
potwierdza czas do decyzji i użyteczność.

## 10. Aktualny stan i jawne blokery

Stan referencyjny odczytujemy z `docs/CONTEXT.md`, `docs/PROGRESS.md`,
`docs/dashboard-state.md`, `docs/current-cleanup-state.md` i Beads — nie z tego
pliku. Znane fakty robocze: inventory ma 601 obiektów (113 ready, 7 partial,
481 blocked); metryki mają ponad 124k facts; 15 zatwierdzonych materiałów ma
manifest metadata-only i `import_pending`. Techniczne exact binding,
measurement history i direct-live guard są domknięte; jakość realnego tekstu,
knowledge import, pełny v2 document, semantic review i UAT nie są domknięte.

Blokery wymagające właściciela: review Service Profiles i materiałów,
credentials/token Keyword Planner, produkcyjny actor/tenant, maintenance window
storage oraz zgoda na realny WordPress draft. Żaden blocker nie może być
przedstawiony jako ukończony bez dowodu.

## 11. Definition of done celu

Cel można zamknąć dopiero, gdy marketer sam wybiera dowolną stronę/usługę,
widzi w kilka sekund realne sygnały, uruchamia pełny pipeline, rozumie źródła,
otrzymuje użyteczny tekst bez slopu, może poprawić sekcję, review jest związane
z exact digest, a WordPress otrzymuje wyłącznie potwierdzony draft-only
ActionObject. Dodatkowo istnieje sanitizowana paczka z prawdziwym nagraniem,
wynikami reviewerów i formularzem Wilku UAT. Do tego czasu goal pozostaje
aktywny, a status komunikujemy jako częściowo gotowy z konkretną listą braków.

## 12. Bramka wykonawcza — wymagania, których nie omijamy

Każda kolejna zmiana musi przejść przez ten sam łańcuch: **wybór → API-owned
snapshot → źródła i świeżość → decyzja → plan → tekst → review → exact
revision → draft-only ActionObject**. Nie uznajemy za gotowe samego ekranu,
zielonych testów, syntetycznego fixture ani odpowiedzi modelu.

Minimalny standard obserwowalnego zachowania:

- kliknięcie dowolnego adresu z inventory musi otworzyć jego realną kartę albo
  zwrócić opisany blocker; nie może wrócić jako fałszywy `block` tylko dlatego,
  że materiał został odczytany w poprzednim kroku;
- pierwszy widok musi pokazać decyzję, metryki, źródło, świeżość i następny krok,
  a ciężkie odczyty nie mogą zasłaniać pracy nieskończonym spinnerem;
- każda zmiana źródła, okresu, jakości, materiału, usługi, inventory lub
  kryteriów zmienia digest i unieważnia zależny plan/review;
- brak porównywalnych okresów nie daje diagnozy spadku, wzrostu, kanibalizacji
  ani przyczynowości — wyświetlamy typowany brak danych;
- model może tylko zaproponować niezatwierdzony artefakt przez serwerowy seam;
  człowiek zatwierdza scope, claims, exact revision i akcję WordPress;
- każdy focused proof ma wskazywać konkretny caller, publiczny seam i wynik
  widoczny dla marketera; pełne `scripts/verify.sh` uruchamiamy dopiero po
  domknięciu wszystkich zależnych slice'ów.

## 13. Protokół long-running task — obowiązuje od nowego goalu

Ten protokół opisuje sposób realizacji długiego celu, nie nową warstwę produktu.
Jest inspirowany oficjalnym wzorcem trwałego celu Codexa dla long-running work
oraz wzorcami OpenAI Cookbook dotyczącymi resilient workflows, eval flywheel i
pracy w tle. W repo pozostajemy przy istniejącym serwerowym Codex app-server;
nie dodajemy drugiego klienta modelowego.

### 13.1 Jeden aktywny goal i wykonywalny plan

- Aktywny goal ma jeden opis rezultatu, granice, Definition of Done i jawne
  blokery. Nie zakładamy nowego goalu dla każdej drobnej czynności.
- `update_plan` pokazuje najwyżej kilka aktualnych kroków; każdy krok ma
  `pending`, `in_progress` albo `completed`. Plan jest kompasem, a nie dowodem.
- Beads jest grafem właścicieli, zależności i handoffów. `PLANS.md` nie jest
  równoległą kolejką TODO i nie kopiuje statusów Beads.
- Na początku każdego odcinka czytamy właściwy `docs/CONTEXT.md`, stan route'u,
  aktywny Bead i tylko wymagane źródła. Nie odzyskujemy stanu z pamięci modelu.

### 13.2 Checkpoint zamiast pozornej ciągłości

Każda iteracja zostawia krótki checkpoint zawierający: fixed commit, zakres,
zmienione seamy, obserwowany wynik, uruchomione proofy, niezakończone ryzyka,
następny krok i właściciela blokera. Po przerwaniu można wznowić pracę z tego
rekordu bez ponownego wymyślania planu.

Procesy trwające długo działają przez managed stack albo jawny background job:

- start zapisuje `run_id`, wejściowy digest, wersję kontraktu i czas;
- GET odczytuje stan, nigdy nie uruchamia modelu ani vendora;
- wynik pośredni nie jest publikowany jako gotowy artefakt;
- retry tworzy nową próbę, a stary run pozostaje czytelny;
- timeout, crash i brak wyniku kończą się typed blockerem bez częściowego zapisu;
- pollujemy krótkimi odcinkami i komunikujemy postęp, zamiast blokować shell lub
  UI nieskończonym spinnerem;
- restart procesu nie może zgubić faktu, że próba się rozpoczęła albo zakończyła.

Nie uruchamiamy tego samego kosztownego modelowego zadania równolegle tylko po
to, żeby „przyspieszyć”. Najpierw sprawdzamy istniejący run, digest i idempotencję.

### 13.3 Najmniejszy kompletny slice i dowód

Kolejność każdego slice'u jest stała:

`claim Beada → caller/public seam → najmniejsza zmiana produkcyjna → focused
falsifier → state/Bead checkpoint → review fixed point → semantic commit → push`.

Proof dobieramy do ryzyka, nie do rozmiaru diffu:

- 0 nowych testów dla dokumentacji, copy i zmian mechanicznych już objętych
  publicznym seamem;
- 1 focused falsifier dla jednego zmienionego kontraktu lub reprodukcji błędu;
- kilka falsyfikatorów tylko wtedy, gdy wymagania mają niezależne failure modes;
- szerokie `scripts/verify.sh` raz przy końcowym cross-surface claimie, nie po
  każdym zielonym teście;
- nigdy nie przedstawiamy testu fixture, screenshotu ani synthetic browser proof
  jako realnego UAT lub dowodu jakości treści.

Każde twierdzenie w handoffie ma bezpośredni artefakt dowodowy: command output,
live API response, test result, rendered browser result albo human decision.
Brak dowodu jest stanem `unknown`/blockerem, nie zaproszeniem do zgadywania.

### 13.4 Model, prompt i review

Model dostaje jeden jasno określony kontrakt i niemutowalny input digest. Nie
prosimy jednej sesji o research, implementację i zatwierdzenie naraz. Model może
proponować; API, człowiek i ActionObject zachowują władzę nad stanem.

Każdy istotny fixed point może mieć najwyżej jeden bounded second-opinion pass
na rolę: `researcher`, `rewrite-maker` albo `checker`. Pass musi mieć własny
katalog poza repo, fingerprint, zakres ścieżek, expected deliverable, lokalny
proof i `disposition.md`. Wynik Claude jest hipotezą klasyfikowaną jako
`accept_and_fix`, `evidence_gap`, `reject_with_evidence`, `follow_up` albo
`human_decision`; nie jest approvalem. Nie retryujemy w tym samym katalogu po
odrzuconym outputcie.

### 13.5 Commit i publikacja

Każdy nowy commit używa semantic headera egzekwowanego przez
`.githooks/commit-msg`. Commit zawiera tylko task-owned paths, a push następuje
po focused proofie i świadomym sprawdzeniu dirty worktree. Stare nagłówki są
historycznym debt, którego nie przepisujemy bez osobnej zgody na rewrite historii.

Commit nie oznacza ukończenia celu. Ukończenie wymaga spełnienia Definition of
Done, świeżego audytu wymagań i dowodów oraz braku nierozwiązanych blockerów
produktowych. Gdy nie można iść dalej przez trzy kolejne goal turns z tym samym
zewnętrznym blockerem, oznaczamy blocker jawnie; nie udajemy postępu i nie
zmieniamy kryteriów sukcesu na łatwiejsze.
