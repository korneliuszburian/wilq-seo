# WILQ — ExecPlan: kompletna produkcja SEO Ekologus dev

> Rola dokumentu: bieżący plan wykonawczy jednego long-running outcome.
> Per-URL stan, dowody i audyt należą do istniejącego journalu, typed WILQ
> records, ActionObjectów i robot manifestu. Bead `wilq-seo-1oa.36.99` jest
> jedynym trackerem. Ten plik nie jest drugim backlogiem ani raportem historii.

## Outcome i stopping condition

Dowieźć kompletną, evidence-bound warstwę SEO dla
`https://ekologus.dev.proudsite.pl`:

- jeden kanoniczny zbiór 214 unikalnych URL-i z ponownie udowodnioną decyzją
  `keep_refresh/merge_redirect/noindex/remove/needs_more_evidence`;
- każdy URL zakwalifikowany po re-adjudykacji do `keep_refresh` z realnie
  napisanym, unikalnym dokumentem: SEO title, meta description, H1, lead,
  sekcje, FAQ, CTA i zweryfikowane linki; liczba takich URL-i wynika z
  dowodów, a nie ze starego baseline'u 57;
- powiązanie każdego twierdzenia ze źródłem na poziomie zdania oraz jawna
  aktualność każdego użytego dowodu i każdej metryki;
- niezależne przeglądy treści, SEO i zgodności ze źródłami, bez zaakceptowanych
  uwag pozostawionych bez rozwiązania;
- exact `the_content` albo ACF component-to-field mapping;
- zatwierdzony draft-only ActionObject, szkic na dev i readback QA dla każdego
  dokumentu, który przeszedł bramki;
- robot/canonical/link graph zgodny z faktycznym stanem całej sitemap.

Cel jest ukończony dopiero wtedy, gdy audyt każdego wymagania oraz istniejący
dziennik z 214 wpisami potwierdzają powyższe dla każdego URL-a. Sam plik,
zielony test, candidate Markdown, plan, liczba słów albo ładny ekran nie są
dowodem napisanej i wdrożonej treści.

Wzorzec long-running goal jest zgodny z oficjalnym OpenAI Docs: jeden trwały
cel, jawny stan końcowy, wskazane źródła, checkpointy i dowody postępu:
<https://learn.chatgpt.com/use-cases/follow-goals>.

## Authority i nieprzekraczalne granice

Owner udzielił autonomicznej zgody na research, lokalne zmiany, WILQ API
read/write, review workflow, exact mapping confirmation, draft-only
ActionObject apply na dev, commit, push, PR, merge i wymagane wdrożenie kodu.

Ta zgoda nie omija typed WILQ safety:

- WordPress może otrzymać wyłącznie nowy szkic na dev przez exact ActionObject;
- publish, update istniejącej treści, delete i bezpośredni vendor adapter są
  nadal poza wspieranym kontraktem;
- nie wolno czytać `.env`, prywatnego packetu content-review ani utrwalać raw
  vendor payloadów;
- nie wolno nazywać synthetic review realnym Wilku UAT ani approvalem prawnym;
- brak źródła, exact identity, writable mappingu lub readbacku jest typed
  blockerem dla konkretnego URL-a, nie zgodą na zgadywanie;
- zablokowany URL nie zatrzymuje niezależnej pracy nad pozostałymi URL-ami.

## Jedna ścieżka prawdy

| Pytanie | Kanoniczny właściciel |
|---|---|
| Jakie URL-e istnieją i jaka jest decyzja? | `docs/content-canonical-ledger-20260828.jsonl` |
| Co już istnieje na dev i czego nie wolno powtórzyć? | `docs/content-dev-state-journal-20260828.json` |
| Jaki jest exact target WordPress/ACF? | `docs/content-dev-authoring-inventory-20260828.json` + typed WILQ target contracts |
| Czy dany keep może wejść do produkcji? | `docs/content-keep-eligibility-20260828.json` i aktualne typed records |
| Jaki tekst jest aktualny? | immutable WILQ `ContentDraftRevision` |
| Czy tekst przeszedł review? | exact revision review + retained independent judge disposition |
| Czy mapping i dev write są zatwierdzone? | mapping confirmation + ActionObject + audit/readback |
| Czy URL jest gotowy dla robotów? | istniejący robot manifest/readback audit |
| Jaki jest aktywny owner i następny slice? | Bead `wilq-seo-1oa.36.99` |

Nie tworzyć drugiego journalu, drugiego manifestu sitemap, osobnego Markdown
checklistu ani równoległego goalu. Gdy schema journalu nie potrafi odróżnić
realnie napisanej treści od candidate-only, rozszerzyć ją deterministycznie w
miejscu i zachować kompatybilny odczyt.

## Per-URL state machine

Każdy `keep` przechodzi kolejno przez poniższe stany. Stan wolno podnieść tylko
na podstawie wskazanego dowodu; cofnięcie źródła, rewizji albo targetu cofa
zależne stany.

| Stan | Dowód wymagany do odznaczenia |
|---|---|
| `inventory_bound` | exact canonical path + dev REST object + disposition `keep` |
| `source_bound` | source pack i service card powiązane z exact work item; fresh evidence IDs |
| `brief_ready` | page intent, query assignments, page assets, claims, CTA i link destinations |
| `canonical_written` | pełna immutable revision; nie candidate-only; wszystkie sekcje source-bound |
| `review_passed` | deterministic QA + niezależny content/SEO/factual review bez otwartych accepted findings |
| `mapping_confirmed` | exact revision + target contract + pełne ACF/the_content selections + confirmation digest |
| `dev_draft_applied` | jeden draft-only ActionObject, successful apply audit, zero publish/update/delete |
| `readback_verified` | exact dev object/readback odpowiada revision, mappingowi, meta, CTA i linkom |
| `robot_ready` | wszystkie wcześniejsze stany oraz canonical/robots/global-link gates |

`blocked` jest ortogonalne i zawsze zawiera: kod, brakujący dowód, ownera,
następny bezpieczny krok i wpływ. Kandydat, historyczna rewizja, stary draft lub
path-only join nigdy nie podnosi stanu automatycznie.

## Baseline, którego nie wolno pomylić z wynikiem

- historyczny podział 214 URL-i: `57 keep / 87 noindex / 46 redirect /
  24 remove`; wszystkie te etykiety są hipotezami do potwierdzenia, nie
  docelowym wynikiem;
- świeży sitemap zawiera 215 wpisów `<loc>`, ale 214 unikalnych URL-i:
  `/baza-wiedzy/` występuje równocześnie w sitemapie stron i kategorii;
- niezależna ponowna ocena dawnych 87 `noindex` wskazała 56 podejrzanych
  decyzji w audycie technicznym i 76 odwróceń w audycie strategicznym;
  13 sporów rozstrzygnął trzeci sędzia. Przed zmianą journalu trwa integracja
  werdyktów per URL; żaden dawny
  `noindex` ani `remove` nie jest wdrażany bez tej integracji, a destrukcyjne
  usunięcie wymaga dodatkowo URL-level backlink proof;
- 175 obserwowanych obiektów REST; wszystkie 57 keep mają exact obiekt;
- keep authoring: 46 `the_content`, 11 ACF;
- 181/181 source-pack refs zweryfikowanych po SHA/size;
- 57 candidate Markdown, 16 753 słowa, 43/57 poniżej 300 słów;
- journal: 11 znanych dev drafts, 8 verified keep drafts;
- obecna projekcja: 13 current revisions, 7 exact service bindings,
  `eligible=0`, `typed_target_context=0`, `reconciled_work_item=0`,
  `source_pack_work_item_binding=0`;
- jeden exact ACF preview, 14 komponentów `human_only`, bez confirmation;
- Keyword Planner pozostaje blocked i nie dostarcza terminów, wolumenów ani CPC.

Te liczby są wejściem. Nie wolno raportować ich jako ukończonej produkcji.

## Kanoniczna produkcja jednego dokumentu

WIP treści wynosi jeden. Read-only research i niezależni sędziowie mogą działać
równolegle na przypiętym fixed poincie; tylko SOL/integrator zapisuje wynik.

1. **Select** — rozpocznij od `GET /api/content/workflow-entry`, następnie
   exact selected workspace i planning proposals. Przed generowaniem sprawdź
   journal, aby nie tworzyć ponownie URL/revision/action.
2. **Bind** — potwierdź exact work item, approved service card, source pack,
   connector freshness oraz WordPress target. Bez tego dokument pozostaje
   candidate-only albo typed blocked.
3. **Research** — zbierz wyłącznie primary/approved sources potrzebne dla
   konkretnej intencji. Metryki page-bound oddziel od batch context. Każdy
   przyszły claim dostaje źródło przed napisaniem zdania.
4. **Prepare text** — WILQ planner → writer tworzy jeden pełny canonical
   document. Tekst ma odpowiadać na intencję, używać konkretów Ekologus i
   usuwać generyczne wypełniacze. Długość wynika z tematu, nie z arbitralnego
   minimum.
5. **Deterministic QA** — schema, H1/title/meta, claim coverage, sources,
   placeholdery, niedozwolone obietnice, CTA destination, link resolution,
   lokalne duplikaty i bezpieczeństwo danych.
6. **Niezależny przegląd** — co najmniej trzy niezależne obszary oceny: treść
   i UX, SEO — w tym intencja i kanibalizacja — oraz zgodność faktów ze
   źródłami. Sędziowie pracują wyłącznie w trybie odczytu. Każda uwaga
   otrzymuje rozstrzygnięcie; zaakceptowana uwaga wraca do jednego autora.
7. **Global QA** — porównaj dokument z dotychczas zatwierdzonym corpus:
   duplicate paragraphs, intent collision, title/H1 collision, link graph i
   nakładanie się CTA. Brak uwag od sędziego nie zastępuje tych testów
   falsyfikujących.
8. **Approve and map** — zapisz exact revision review, odczytaj bieżący target,
   potwierdź każde pole ACF albo cały `the_content`. Partial ACF clone jest
   niedozwolony.
9. **Dev draft** — utwórz i zastosuj jeden draft-only ActionObject. Nigdy nie
   retry ze starym digestem; `409` wymaga świeżego odczytu.
10. **Readback** — sprawdź exact object ID, revision digest, mapped fields,
    SEO assets, CTA i linki. Dopiero wtedy aktualizuj stan URL-a w istniejącym
    journalu/robot manifest.

## Kolejność fal

1. **Wave 0 — ponowna ocena i uzgodnienie stanu, bez regeneracji:** rozstrzygnij całe
   214 URL-i, zaczynając od 87 historycznych `noindex`, następnie sklasyfikuj
   istniejące 57 kandydatów, 13 current revisions, 8 verified drafts i 9
   existing-generation identities jako `reuse / refresh / write / blocked`
   z exact dowodem. Po integracji przelicz realną liczbę dokumentów do
   napisania oraz targetów wymagających scalenia.
2. **Wave 1 — najpełniejsze powiązanie ze źródłami:** BDO i kolejne URL-e wskazane przez
   workflow-entry, które mają exact work item, approved service card, fresh
   sources i bieżący target. Pierwszy dokument ma przejść pełną ścieżkę aż do
   dev readback; nie kończyć na planie ani candidate Markdown.
3. **Wave 2 — the_content:** produkować partiami dopiero po zaakceptowaniu
   wzorca Wave 1; każdy dokument nadal ma osobną rewizję i review.
4. **Wave 3 — ACF:** obsługiwać layoutami; każda sekcja i pole wymagają exact
   selection. Nie mapować na podstawie podobnej nazwy layoutu.
5. **Wave 4 — global sitemap QA:** wszystkie 214 URL-i, canonical/robots,
   redirects, missing pages, metadata, link graph, duplicate/cannibalization i
   finalny readback.

Jeżeli runtime/API blokuje kanoniczną ścieżkę dla wybranego URL-a, naprawić
najmniejszy publiczny seam z focused falsifierem, a następnie natychmiast wrócić
do tego samego dokumentu. Naprawa infrastruktury nie jest samodzielnym wynikiem
content production.

## Standard anty-slop

Dokument nie przechodzi review, jeśli zawiera choć jedno z poniższych:

- generyczny wstęp możliwy do wklejenia na dowolnej stronie;
- powtórzenie tej samej myśli innymi słowami dla zwiększenia długości;
- nieudowodnioną przewagę, skuteczność, zgodność prawną lub wynik SEO;
- akapit bez funkcji w intencji strony albo bez source/claim lineage;
- sztuczne keyword stuffing, meta-komentarz AI, placeholder lub prompt residue;
- CTA bez istniejącego destination i jawnej relacji z usługą;
- link do nieistniejącego, redirectowanego albo niezatwierdzonego celu;
- FAQ kanibalizujące osobny URL zamiast odpowiadać na pytanie tej strony;
- H1/title/meta zduplikowane lub niespójne z primary intent;
- tekst z publicznej starej strony użyty jako authority zamiast materiału
  historycznego do krytycznej oceny.

## Dowody checkpointu

Każdy update SOL podaje:

- ownera i jednego writera;
- exact URL/work item/revision/action;
- źródła i evidence IDs;
- zmienione ścieżki;
- focused falsifier i wynik;
- fixed-point review oraz disposition findingów;
- co jest realnie napisane/zaaplikowane/odczytane;
- czego wynik nadal nie dowodzi;
- następny URL albo konkretny blocker.

Repo proof dobieramy do ryzyka zgodnie z `AGENTS.md`; szerokie
`scripts/verify.sh` uruchamiamy raz przy cross-surface/release fixed poincie, nie
po każdym tekście. Globalny content audit musi ostatecznie potwierdzić:

- exact 214 unikalnych URL-i i set equality z deduplikowaną sitemapą;
- 214/214 ponownie rozstrzygniętych decyzji z dowodami i disposition
  niezależnych sędziów;
- wszystkie finalne `keep_refresh` w stanie `canonical_written` albo z jawnym
  typed blockerem i ownerem;
- 0 nieudowodnionych rendered claims;
- 0 niedozwolonych exact/near duplicates i intent collisions;
- wszystkie CTA/link destinations istnieją i są zgodne z disposition;
- każdy applied draft ma ActionObject/audit/readback lineage;
- `publish_allowed=false` i brak produkcyjnej publikacji.

## Restart

Po wznowieniu czytaj kolejno: `AGENTS.md`, ten plik, Bead
`wilq-seo-1oa.36.99`, `docs/content-dev-state-journal-20260828.json`, aktualny
main/CI i ostatni accepted fixed point. Nie odtwarzaj zielonych odczytów i nie
generuj ponownie zakończonego URL-a. Następny owner bierze dokładnie jeden URL
z pierwszego niedomkniętego stanu w istniejącym journalu.
