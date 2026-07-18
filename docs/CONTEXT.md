# WILQ — kanoniczny kontekst produktu i runtime

Stan na: 2026-07-18.

Ten plik jest pierwszym recovery entrypointem po utracie kontekstu. Pokazuje
docelowy produkt, aktualną prawdę, aktywny priorytet i granice. Nie jest
changelogiem. Historia pozostaje w git, zamkniętych Beads i archiwach progress.

## Recovery

Czytaj w tej kolejności:

1. `AGENTS.md` — stałe reguły, bezpieczeństwo, runtime i gotchas.
2. `docs/CONTEXT.md` — pełna bieżąca mapa produktu.
3. `docs/goals/001-goal.md` — aktywny cel pilota.
4. `docs/current-cleanup-state.md` — aktualne seamy i zakończony cleanup.
5. `docs/dashboard-state.md` — prawda per route.
6. `docs/PROGRESS.md` — najnowszy krótki dowód i luki.
7. `PLANS.md` — długotrwały ExecPlan i decyzje.
8. `rtk bd prime` oraz `rtk bd ready --json` — operacyjny graf pracy.

## Czym jest WILQ / Better BDOS

WILQ to lokalny, API-first Marketing Operating System dla Ekologus. Ma
przenieść jakość operacyjną BDOS na cały marketing: mniej klikania i ręcznego
łączenia danych, szybsze decyzje, zakodowana wiedza ekspercka, bezpieczne
wykonanie i mierzalna pamięć wyniku.

`evidence-first` jest warstwą bezpieczeństwa, nie definicją produktu. Pełny
operator WILQ musi jednocześnie:

1. przyjąć normalne polecenie marketera albo poprowadzić prosty dashboard flow;
2. zebrać aktualne dane, kontekst Ekologus i właściwe reguły eksperckie;
3. zakwestionować słabe założenie oraz wskazać jedną decyzję i jej priorytet;
4. zakończyć nazwane zadanie, a nie tylko wygenerować diagnozę lub raport;
5. skrócić czas do decyzji/wyniku w sposób możliwy do zmierzenia;
6. dla zapisu przejść `validate → preview → review → confirm → audit`;
7. zachować kontekst, wersje, decyzje i historię tak, aby można było wrócić do
   pracy po tygodniach;
8. po wykonaniu otworzyć okno pomiaru i zaproponować wniosek bez automatycznego
   claimu sukcesu.

WILQ API jest mózgiem. Dashboard, Codex skills i ograniczony lokalny executor
używają tych samych typed contracts. MCP może być adapterem, nigdy drugim
mózgiem. Browser nie łączy się z modelem bezpośrednio.

### Decyzja z benchmarku BDOS

Źródło: materiał z `bdos.ai` przekazany przez ownera 2026-07-16. Materiał jest
benchmarkiem mechaniki produktu, nie dowodem lokalnej implementacji ani
uprawnieniem do kopiowania jego obietnic.

- **Adoptujemy:** conversational/one-command entry, kompletne workflowy,
  time-to-result, zakodowane API traps i wiedzę ekspercką, cross-source
  analysis, durable client memory oraz safe mutation engine.
- **Adaptujemy:** BDOS jest głównie Google Ads; WILQ stosuje ten wzorzec do
  Treści/SEO, Ads, GA4, Merchant, Localo, social i wiedzy Ekologus.
- **Odrzucamy jako nieudowodnione:** obietnice oszczędności czasu, przychodu,
  ROAS, pełnej automatyzacji, bezpieczeństwa produkcyjnego lub jakości 10/10,
  dopóki lokalny workflow i człowiek ich nie potwierdzą.
- **Falsifier:** realny marketer ma ukończyć zadanie szybciej i lepiej niż
  ręcznie, z wynikiem, który obroni w review. Sam endpoint, test lub screenshot
  nie spełnia tego warunku.

## Aktualna mapa możliwości

| Capability | Stan realny | Działa | Brak / ryzyko |
| --- | --- | --- | --- |
| Daily Command | techniczny pilot działa | świeże dowody, priorytet, blocker i bezpieczne akcje | realny werdykt Wilka i zmierzona oszczędność czasu |
| Evidence Engine | działa | evidence IDs, connectors, freshness, blocked claims | nierówna głębokość konektorów; dowód sam nie kończy pracy |
| Knowledge Compiler / Service Profile | częściowo | source-backed karty, lifecycle, review actions i claim policy; live API ma 21 source-facts, a BDO i outsourcing mają `approved_current` | 8 z 15 materiałów pozostaje `import_pending`; pozostałe karty/usługi nadal wymagają owner review |
| Content Ops | mechaniczny loop działa, jakość nie | jeden entrypoint, planning reviews, exact revisions, Codex proposal, human review, dev draft-only, measurement/learning contracts | wybór konkretnej usługi/strony/sekcji jest zbyt pośredni; realny tekst ma około 5/10; brak owner-reviewed knowledge i Wilku UAT |
| Ads Doctor | read/review działa | live campaigns/search terms/recommendations, diagnostyka, review-only ActionObjects | brak podstaw do części claims finansowych; Keyword Planner blokowany zewnętrzną gotowością tokena developerskiego |
| Campaign Builder / custom segments | częściowo | struktury i preview/review contracts | brak dowodu pełnego bezpiecznego realnego build/apply w pilocie |
| GA4 Analyst | read/review działa | rozdziela jakość ruchu od problemów pomiaru | braki pomiaru blokują konwersje, revenue i ROAS claims |
| Merchant Operator | read/review działa | agregaty produktów, issue queue, readiness i ActionObject review | issue occurrences nie są listą unikalnych SKU; cold diagnostics około 6 s; brak vendor write |
| Localo Operator | częściowo | read-only aggregate/ranking/GBP evidence i honest blockers | za mało dowodu do mocnych lokalnych tez i mutacji GBP |
| Social Publisher | zablokowany poprawnie | review-only kierunki i duplicate guard | brak zatwierdzonego historycznego inventory LinkedIn/Facebook |
| Action Engine | kontrakt działa | validate, preview, review, confirm, impact, audit; destructive writes zablokowane | realne vendor writes wymagają osobnej zgody i proofu |
| Measurement Loop | techniczny kontrakt działa | publication-bound windows, server-owned outcome, review-only learning proposal | brak realnego zaakceptowanego publication event i okresu wyniku |
| Eval Harness / skills | działa technicznie | deterministyczne smokes, Codex evals, polski/evidence/action checks | wynik eval nie zastępuje realnej użyteczności i jakości pracy |
| Codex executor | lokalny kontrakt działa | Codex app-server przez istniejący `codex login`, bez API keya | ergonomia osadzenia w dashboardzie i realne długie sesje wymagają proofu |
| Produkcja | nieudowodniona | prywatny loopback-only pilot i lokalne credential sources | auth, TLS, tenant/actor contract, monitoring, HA, rotation i maintenance procedures |

## Priorytet P0: Content Ops jako pierwszy pełny Better BDOS workflow

Owner ustalił, że cały WILQ ma osiągnąć powyższy standard, ale Treści i SEO ma
być pierwszym pionem dopracowanym maksymalnie i jak najszybciej przekazanym
marketerowi.

Docelowa jedna sesja:

```text
„Popraw treść dla usługi/strony/sekcji X”
→ wybór exact usługi, strony, intencji, odbiorcy i CTA
→ GSC + WordPress + Ahrefs + Ads/Planner tylko przy exact mappingu
→ inventory, canonical, duplicate i internal-link checks
→ reviewed Service Profile + Sales Brief + Claim Ledger
→ reviewed scope i mapa sekcji
→ grounded Codex proposal na exact revision
→ automatyczna diagnoza jakości + SEO/content/marketer review
→ iteracje i human acceptance dokładnej wersji
→ revision-bound WordPress dev draft-only
→ publication-bound measurement window
→ review-only learning proposal
```

Pierwszy realny case: karta `ekologus_service_bdo_reporting` oraz publiczna
strona BDO. Live API potwierdza obecnie `approved_current` dla BDO i dla
`ekologus_service_environmental_consulting_outsourcing`; nadal nie wolno
udawać finalnego claimu prawnego/obowiązkowego ani publikacji bez exact review.

Aktywny graf:

- `wilq-seo-1oa.36` — epic pełnego marketer-grade Content Ops;
- `wilq-seo-1oa.36.1` — pierwszy slice API-owned wyboru usługi, strony i sekcji
  jest technicznie domknięty na BDO;
- `wilq-seo-1oa.36.2` — odzyskuje dynamiczny planning po odrzuceniu
  hardkodowanego slice'a BDO; dalszy kontrakt ma obsłużyć co najmniej dwie
  usługi przez te same API-owned reguły;
- `wilq-seo-1oa.35` — zamknięty folder demonstracyjny; artefakt przekazania,
  nie substytut ukończonego content loopu.

## Aktualny dowód contentu

- `/content-workflow` jest jedynym głównym entrypointem.
- Bieżący selected work item dotyczy strony BDO i jest na kroku `scope`.
- Exact sekcja `Co wiemy z zapytań: bdo dla kogo` jest wybranym focusem sesji
  i przeżywa reload tylko z pasującym `planning_digest`; zmieniony plan
  unieważnia stary fokus. Wybór nie zapisuje planning review ani approval.
- Exact snapshot obejmuje 11 page-scoped wierszy GSC; bieżąca karta zakresu
  agreguje 65 wyświetleń, 0 kliknięć i najlepszą średnią pozycję 9,00. UI i
  eval pokazują cztery najwyższe wiersze oraz pełną liczność.
- Scope i section map nie mają human approval.
- Dynamic planning v2 ocenia zawsze dziesięć źródeł, ale dopuszcza do modelu
  tylko `used` lineage z exact landing/service/inventory matchu. WordPress
  wymaga jednego rekordu canonical i rozwiązywalnego evidence właściwego
  konektora; freshness jest oceniana per connector. Dwa piloty przechodzą ten
  sam kontrakt wyłącznie na syntetycznie zatwierdzonych kartach.
- Search terms Ads mogą zasilić plan wyłącznie przez kompletny, świeży batch z
  faktycznie klikniętym landingiem i pięcioma metrykami z tego samego evidence;
  stare, częściowe, wrażliwe i niepasujące dane są jawnie odrzucane.
- Realny Codex proposal został poprawnie związany z wersją i dowodami, lecz
  quality review zwrócił `needs_changes`; jakość tekstu pozostaje około 5/10.
- Kolejka ma 5 kandydatów, z czego 4 są actionable. BDO jest pierwszym
  wykonalnym exact work itemem i jego wybór przeżywa reload przez typed URL
  search.
- Karta BDO ma public source lineage i `approved_current`; wspiera aktualny
  scope do review, ale nie finalny claim prawny ani publikację.

Ocena 10/10 wymaga realnej paczki tekstów i werdyktu marketera. Nie może zostać
nadana przez Codex, testy ani ownera kodu bez review treści.

### Baza wiedzy Ekologusa

`/knowledge` pokazuje teraz najpierw rejestr realnych, zredagowanych faktów
źródłowych. Legacy karty i playbooki pozostają pomocniczą warstwą operacyjną i
nie są przedstawiane jako wypowiedzi Ekologusa. Odnaleziony zatwierdzony korpus
15 plików z repozytorium materiałów jest opisany w
`docs/research/approved-ekologus-materials-2026-07-17.md`; jego treść nie jest
jeszcze kopiowana do WILQ. Import wymaga redakcji, lineage, hashy i review
ownera. Panel pokazuje metadata-only manifest 15 materiałów jako `import
pending`, więc marketer widzi realny zakres korpusu bez dostępu do surowego
tekstu; do tego czasu source-backed planning pozostaje jawnie `review_required`.

## Runtime

Kanoniczny lokalny stack:

```bash
rtk scripts/local_stack.sh start
rtk scripts/local_stack.sh status
```

- API: `http://127.0.0.1:8000`
- Dashboard: `http://127.0.0.1:5173/command-center`
- Python/API: zawsze `rtk uv run ...`
- Model runtime: istniejący lokalny Codex login/app-server; brak OpenAI API keya,
  Agents SDK, Ollamy i drugiej ścieżki generowania.

## Granice i zewnętrzne bramki

- Brak evidence/source/freshness oznacza brak rekomendacji.
- Brak reviewed knowledge oznacza review packet albo blocker, nie finalny claim.
- Każda mutacja wymaga ActionObject i audytu; publish/update/delete są poza
  content journey.
- Nie wykonuj realnej publikacji, vendor write, storage migration ani secret
  rotation bez osobnej zgody i właściwego okna.
- Nie claimuj produkcji, auth, TLS, multi-tenant, aktualnego prawa, jakości
  retrievalu, efektu marketingowego ani expert acceptance bez dowodu.
- Nie naprawiaj produktu w skill promptach. Najpierw typed WILQ API/schema/
  view-model, potem dashboard i skill.
- Martwe artefakty usuwaj dopiero po potwierdzeniu braku referencji.

## Po każdym slice

1. Focused proof ryzyka, które zmieniono.
2. Aktualizacja bieżącego state record zamiast dopisywania kroniki.
3. Komentarz i zamknięcie właściwego Beada po spełnieniu kryterium.
4. Świadomy commit i push bez `AGENTS.md`, jeśli jest user-dirty.
5. `rtk bd ready --json` i przejście do następnego potwierdzonego zadania.
