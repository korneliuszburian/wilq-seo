# Ekologus: evidence-bound produkcja treści i SEO

> Rola: `current state` i długotrwały ExecPlan jednego celu. Beads jest kolejką
> wykonawczą, a `docs/content-status-214.csv` jedynym kanonicznym dziennikiem per
> URL. Ten dokument nie duplikuje tych rekordów.

## Outcome

Doprowadzić całą sitemapę `ekologus.dev.proudsite.pl` do audytowalnego stanu:

- wszystkie 214 URL-i mają zweryfikowaną decyzję `keep/noindex/redirect/remove`;
- każdy z 57 URL-i `keep` ma exact lineage od inventory i źródeł do bieżącej
  immutable revision, review, target mappingu i readbacku draftu dev albo
  prawdziwy zewnętrzny typed blocker;
- priorytet produkcji wynika z page-bound danych WILQ API, ale brak metryki nie
  jest zerem ani powodem odrzucenia strony;
- nie powstaje AI slop: tekst odpowiada intencji, wnosi własną wartość, nie
  powiela korpusu, nie nadclaimuje i przechodzi deterministic oraz niezależne
  review;
- pipeline, prompty, klasyfikacje, mapowanie ACF/`the_content` i QA pozostają
  reużywalne po refaktorze;
- wykonanie kończy się wyłącznie create-only draftem dev. Public publish,
  update i delete pozostają niedozwolone.

## Authority i źródła prawdy

1. `docs/content-status-214.csv` — 214-row journal i finalna projekcja stanu.
2. WILQ SQLite/API — evidence, immutable revisions, review, ActionObject, audit.
3. Sitemap/public/dev readback — tożsamość URL, canonical i exact target proof.
4. Beads — jedyna kolejka, zależności, WIP, proof i handoff.
5. Ten plan — kolejność, bramy i kryterium zakończenia, nie rejestr URL-i.

Nie wracamy do historycznego JSON journalu ani snapshotu eligibility jako
bieżącej prawdy. Nie regenerujemy dobrej rewizji: `approved` jest reużywane,
a `needs_changes` może utworzyć wyłącznie exact immutable child revision.

## Baseline 2026-09-10

- 214 URL-i: `57 keep / 87 noindex / 46 redirect / 24 remove`.
- `keep`: 18 bieżących approved revisions, 17 semantic zero-findings, 1 semantic
  unavailable (REACH), 8 zweryfikowanych dev draft readbacków, 0 robot-ready.
- frontier: 8 legacy dev-readback observed (tylko 1 ma `confirmed_the_content`;
  pozostałe 7 wymaga reconciliation), 8 current-approved z dalszym gate'em,
  2 historyczne non-reusable, 37 source/service/work-item blocked, 2 z
  potwierdzonym zewnętrznym dev-REST credential blockerem.
- 45 `keep` to editorial, 7 service, 5 landing/hub. Landing/hub nie ma jeszcze
  pełnej typed authorization path.
- WILQ ma page-bound GSC dla 38/57 keep; 16 ma wpis bez metryk, 3 nie ma matchu.
  Snapshot GSC obejmuje jeden dzień `2026-09-06`, collected `2026-09-09`,
  `partial_possible`; służy do kolejności, nie do obietnic wyniku.
- GA4 jest settling/unverified i nie page-level. Ahrefs jest manualnym domain
  snapshotem i nie page-level. Oba są kontekstem, nie tie-breakerem URL-i.
- aktualny managed runtime raportuje 1/12 configured connectors i 10 missing
  credentials; nie wolno odczytywać ani ujawniać wartości `.env`.
- `target_unavailable` występuje przy 3 keep: dwa direct dev-REST credential
  blockers i osobny REACH work-item/semantic blocker.

## Priorytet metryczny

Pierwsza dziesiątka page-bound GSC z evidence
`ev_refresh_refresh_google_search_console_0e332cb3bb35`:

| # | URL | Wyświetlenia / kliknięcia / zapytania | Następny exact seam |
|---:|---|---:|---|
| 1 | `/bdo-co-musi-wiedziec-przedsiebiorca` | 660 / 1 / 16 | audit legal freshness/readback; bez ponownego pisania |
| 2 | `/operat-wodnoprawny-wszystko-co-musisz-wiedziec` | 145 / 0 / 103 | confirm target mapping; bez ponownego pisania |
| 3 | `/europejski-zielony-lad-co-to-takiego` | 109 / 4 / 18 | restore dev REST, retry target discovery |
| 4 | `/remediacja-czym-jest-na-czym-polega-kiedy-jest-wymagana` | 98 / 0 / 41 | evidence-bound revision |
| 5 | `/outsourcing-srodowiskowy-elastyczne-rozwiazanie-dla-twojej-firmy` | 50 / 0 / 29 | evidence-bound revision |
| 6 | `/oferta/doradztwo-i-outsourcing-ekologiczny` | 49 / 0 / 27 | confirm target mapping |
| 7 | `/oferta/szkolenia` | 43 / 0 / 30 | confirm target mapping |
| 8 | `/pozwolenie-zintegrowane-wymagania-i-procedury-ippc` | 31 / 1 / 14 | repair current work-item identity |
| 9 | `/` | 30 / 0 / 24 | confirm target mapping |
| 10 | `/ocena-wplywu-projektow-na-srodowisko` | 29 / 0 / 16 | confirm target mapping |

Kolejność wykonawcza = potencjał metryczny × gotowość. Po naprawie seamów
najszybsze existing-revision deliveries to #6, #7 i #9; pierwszy nowy content
slice to #4 albo #5. #1–2 nie wolno pisać ponownie. #3 pozostaje credential
blocked, dopóki runtime nie potwierdzi dev REST.

## Standard jakości i research

Każdy URL `keep` dostaje wersjonowany research packet: exact intent i query
cluster, canonical owner, content kind, odbiorca/problem/trigger, approved facts,
blocked claims, freshness, legal/source requirements, CTA destination, internal
links i source/evidence IDs. Wymagania pochodzą z aktualnych, bezpośrednich
źródeł: Google Search Central i Search Quality Rater Guidelines, źródeł
urzędowych dla prawa, badań naukowych tam, gdzie rzeczywiście wspierają
mechanizm, oraz jawnie ograniczonych praktyk UX/content. Każde źródło ma URL,
datę odczytu, zakres autorytetu, freshness i decyzję `adopt/reject/lab-test/defer`.
`defer` wymaga nazwanego ownera i warunku ponownego sprawdzenia; nie oznacza
odrzucenia i nie może pozostać bezterminowym stanem domyślnym.
Packet jest typowanym immutable rekordem związanym z current work itemem i
revision-input digest, nie luźnym Markdownem ani promptowym blobem.

Kolejność bram:

1. schema, lineage, blocked-claim i regulatory deterministic checks;
2. readability, struktura, answer directness, repetition, CTA i link safety;
3. corpus-wide duplicate/intent/canonical/link graph na wersjonowanym snapshotcie
   przed revision i ponownie przed readbackiem kohorty;
4. niezależny content/UX judge;
5. niezależny SEO/intent/cannibalization/metadata judge;
6. niezależny factual/regulatory/source-fidelity judge;
7. WILQ semantic review dokładnej revision.

Deterministic gate obejmuje `long_sentence`, `heading_answer_mismatch`,
`heading_exaggeration`, `vague_answer_phrase`, `thin_section`, `wall_of_text`,
`working_note`, `duplicate_paragraph`, weak CTA, język, source/claim oraz
privacy/consent. Byline/author pozostaje `lab-test`.

DeepSeek V4.1 Flash (`opencode-go/deepseek-v4.1-flash`) jest advisory judge. Nie może
nadpisać deterministic failure ani nadać approval. Każdy finding ma lokalną
dyspozycję `accepted/rejected/deferred` z dowodem.

Zakazane skróty: magic SEO score, długość tekstu jako jakość, keyword stuffing,
substring coverage jako dowód intencji, current-vs-current uniqueness,
page-level wnioski z domain-level Ahrefs/GA4, samocytowanie Ekologus jako
niezależny proof, syntetyczny PASS i claim o rankingu/konwersji bez pomiaru.

## Plan dostawy

Każdy punkt niżej jest osobnym Beadem, jednym observable resultem, jednym
writerem w osobnym worktree, focused falsifierem, fixed-point Spec+Standards
review i jednym cohesive commitem. WIP pozostaje dokładnie 1.

### S0 — utrwalenie planu i projekcji

Zastąpić stare odwołania w `PLANS.md` i `docs/CONTEXT.md` do JSON/closed Bead
kanonicznym CSV, opublikować graf zależności i zachować snapshot eligibility
wyłącznie jako `historical/reference`. Scalić validator z merged `main`, dodać
schema-version guard, zablokować staremu niekompatybilnemu exporterowi zapis do
journalu i podpiąć focused check do CI. Falsifier: 214-row validator przeciw
authoritative DB + destructive-export regression + `git diff --check`.

### S1 — exact identity reconciliation

Dodać append-only `ContentDeliveryRecord` z `final_disposition`, `content_state`,
`delivery_status`, `robot_ready`, gate evidence i typed blocker enum. W nim
`ContentDeliveryIdentityBinding`: canonical path/public URL,
current work item, opcjonalny retained owner, classification run/digest,
inventory evidence, source-row digest, binding digest, actor/time i status
`exact_current | reconciled_retained | blocked`. Blocker mapuje seam, reason,
evidence i next safe step. Path-only/fuzzy join fail-close.

### S2 — source-pack binding i research registry

Dodać append-only `ContentSourcePackBinding`: pack identity/hash, current work
item, whitelisted source facts/evidence i fresh context digest. Odświeżyć
registry z source-to-decision, niezależnie zreaudytować masową pulę faktów i
stworzyć per-URL packet bez kopiowania raw/private materiałów do promptów.

### S3 — trzy content kinds

Zachować istniejące service/editorial contracts i dodać jawny typed
`landing_or_hub` receipt/authorization. Landing nie udaje artykułu ani service
card. Każdy kind ma własne wymagane fakty, CTA i duplicate/intent gates.

### S4 — jedna reużywalna production command

Spinać istniejące seamy `prepare → authorize → plan → immutable revision` dla
jednego current work itemu. Command jest idempotentny, sprawdza journal przed
generacją i wiąże revision z identity/source packet/context digests. Nie tworzy
drugiego planera ani batchowego autopublish.

Osobny append-only generation order/attempt falsifier uruchamia command dwa razy
dla approved/readback row i potwierdza brak nowej próby, model call i revision.

### S5 — exact review convergence

Review należy do `revision_id + digest`. Deterministic checks uruchamiają się
przed trzema niezależnymi judge'ami i WILQ semantic review. Wszystkie findings
muszą mieć dyspozycję; accepted critical finding wymusza exact child revision.
Naprawić REACH work-item availability bez syntetycznego semantic PASS.

Realizacja dzieli się na trzy atomowe Beady: deterministic gate; typed
`ContentIndependentReviewRun` z rolą/model/version/evidence i persisted finding
disposition; osobny REACH recovery. Jeden run nie może udawać trzech ról.

### S6 — exact target discovery i mapping

Obsłużyć observed native `the_content` również dla `page`, wyłącznie po direct
REST read. ACF wymaga kompletnego component→field/writable-leaf profile,
pełnego klonu i jawnego confirmation receipt; podobny slug/layout nie wystarcza.
Credential absence, ambiguous target i schema mismatch pozostają typed blocker.

Realizacja dzieli się na page `the_content` + typed discovery failures oraz
osobny full-clone ACF mapping. Siedem legacy readbacków bez mappingu wraca do
reconciliation i nie liczy się jako exact completion.

### S7 — create-only ActionObject i exact readback

Dodać `content_dev_draft_create` do globalnego WordPress readbacku, utrwalić
redacted expected body/ACF/meta/CTA digests i porównać je z authoritative GET.
Stale confirmation, partial ACF i existing-post update fail-close. Zero
public publish/update/delete.

Realizacja dzieli się na persisted expected/observed digest receipt oraz branch
globalnego readbacku dla `content_dev_draft_create`.

### S8 — trzy representative vertical proofs

Przeprowadzić po jednym URL-u przez całość:

1. editorial + `the_content` — kandydat metryczny z nową revision;
2. service + ACF — current-approved bez ponownej generacji;
3. landing/hub — nowy typed kind.

Każdy kończy się exact dev draft readback lub prawdziwym external blockerem.
Dopiero trzy zielone ścieżki odblokowują kolejne kohorty.

### S9 — produkcja kohort 57 keep

Kohorty są dynamiczną projekcją WILQ, nie ręczną listą w planie:

1. existing approved → mapping/readback;
2. page-bound GSC + source-ready → research/revision/review/delivery;
3. brak page metrics, lecz source-ready → najlepsze standardy i uczciwy brak
   priorytetu metrycznego;
4. source/service/work-item repairs;
5. external blockers.

Po każdym URL-u materializer aktualizuje dokładnie jeden wiersz journalu.
Retry używa persisted order/attempt i nigdy nie regeneruje ukończonego etapu.

### S10 — global SEO/content QA i polityki non-keep

Zbudować wersjonowany corpus-wide canonical/intent/duplicate/FAQ collision
graph, orphan i
internal-link audit, title/meta uniqueness i claim checks, właściwość structured
data, content-level accessibility/heading/link-purpose/mobile checks oraz CTA
destination validation. Zweryfikować 87 noindex, 46 redirect i 24 remove jako
decyzje/paczki dev; bez produkcyjnego delete/redirect apply.

Preflight graph działa przed revision i jest odświeżany po każdej kohorcie.
Finding zmieniający intent/canonical/link lub visible claim unieważnia downstream
review/mapping tej revision. `next_action` dla non-keep ma brzmieć
`prepare_*_policy_review`, nigdy `execute_*`.

### S11 — runtime-owned journal i robot-ready gate

Jedna read-only `ContentDeliveryStatusProjection` materializuje CSV z runtime.
Validator porównuje revision, reviews, semantic disposition, target confirmation,
ActionObject audit/readback, metadata, CTA/link graph i global QA. `robot_ready`
może przejść na true wyłącznie po wszystkich gate'ach, nigdy ręcznie.

Każdy wiersz ma `updated_at`, `last_verified_at`, source freshness i page-bound
metric evidence/dimension digest albo jawne `metric_unavailable`. Stary exporter
nie jest writerem journalu. Projekcja i robot gate są osobnymi atomowymi Beadami.

### S12 — final proof i delivery

Uruchomić focused falsifiers, raz pełne `scripts/verify.sh`, pełne CI, niezależny
fixed-diff Spec+Standards review i DeepSeek advisory review z dyspozycją.
Scalić wymagane PR-y, zamknąć Bead dopiero po weryfikacji merged main oraz
uruchomić managed API/dashboard na merged SHA. Dev pozostaje miejscem UAT;
produkcja i claim skuteczności pozostają poza zakresem.

## Zależności

```text
S0 → S1 → S2 → S3 → corpus preflight → S4 → S5 → S6 → S7 → S8 → S9
                                                    ↓              ↓
                                          cohort QA/readback → S10 final QA
                                                                   ↓
                                                               S11 → S12
runtime credentials ───────────────────────────────→ S6/S7/S9
```

Research może pogłębiać packet następnej strony równolegle jako read-only, ale
nie może pisać stanu. Writer pozostaje jeden. External credential/source blocker
zatrzymuje tylko swój URL; kolejny URL może ruszyć dopiero po zapisaniu blokera
i zakończeniu bieżącego Beada zgodnie z WIP=1.

## Proof i definicja zakończenia

Cel jest kompletny wyłącznie, gdy:

1. validator potwierdza exact 214 rows i `57/87/46/24` przeciw authoritative DB;
2. 57/57 keep ma exact mapped dev draft readback albo prawdziwy external typed
   blocker; legacy readback bez mapping receipt nie spełnia tego punktu;
3. żadna dobra current revision nie została bez potrzeby wygenerowana ponownie;
4. wszystkie revisions mają source/claim lineage, wszystkie critical findings
   są rozwiązane, a legal claims mają aktualny official-source review;
5. target mapping, pełny ACF/`the_content`, meta, CTA i linki przechodzą exact
   readback; żaden partial clone nie jest uznany za sukces;
6. global duplicate/intent/canonical/link/structured-data/accessibility QA jest
   zielone lub ma per-URL typed blocker;
7. privacy/consent gate nie ujawnia PII i blokuje nieuprawnione dane osobowe;
8. nie wykonano public publish/update/delete i nie ujawniono credentials;
9. pełne CI jest zielone na merged main, wszystkie wymagane PR-y są scalone,
   Bead zamknięty, a managed API/dashboard są ready na tym SHA.

Brak źródła, credentials/consent, exact targetu lub nieweryfikowalny claim może
być terminalnym external blockerem. Brak seamu, bindingu, klasyfikacji, promptu,
review harnessu, mapowania albo walidatora jest pracą do naprawienia, nie
usprawiedliwieniem zakończenia.
