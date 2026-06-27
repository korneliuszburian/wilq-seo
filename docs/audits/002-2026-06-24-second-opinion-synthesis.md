# 2026-06-24 Synteza 2nd Opinion

Superseded note, 2026-06-27: URL and content-placement notes in this synthesis
predate the product correction that `ekologus.pl` is the public canonical
content home and dev preview hosts are optional design/staging context only.
Treat any dev-site migration or old-to-new mapping guidance below as
historical input, not current implementation guidance.

Ten plik kondensuje trzy zewnętrzne raporty 2nd opinion z 2026-06-24. Nie jest
nowym źródłem prawdy produktowej. Służy do sterowania kolejnymi slice'ami po
sprawdzeniu aktualnego repo, WILQ API i dashboardu.

## Konsensus

Wszystkie raporty zgadzają się co do jednego obrazu:

- WILQ nie jest już prompt-packiem ani statycznym raportem. Ma realny
  API-first rdzeń decyzyjny: WILQ API, typed schemas, diagnostics endpoints,
  ActionObjecty, evidence IDs, dashboard routes, skill contracts i evale.
- Największa obecna wartość to evidence-backed review cockpit oraz asystent
  planowania treści dla Ekologus, nie pełny BDOS-class execution OS.
- Najmocniejsza ścieżka demo jest wąska: Command Center -> Merchant ->
  Content Planner -> Ads Doctor -> GA4. Localo pokazujemy tylko jako
  read-only/local readiness, chyba że aktualne API evidence uzasadnia więcej.
- Content jest dziś najwyższą wartością dla marketera. Użyteczną jednostką nie
  jest "pomysł na temat", tylko strukturalny brief lub plan draftu z faktami
  źródłowymi, intencją, H1/H2/FAQ/CTA, brakującymi dowodami i zakazanymi
  claimami.
- Ads, Merchant, GA4 i Localo są użyteczne jako guardrailed review workflows.
  Nie wolno ich prezentować jako CPA/ROAS/wasted-budget/feed-repair/
  local-uplift automation, dopóki nie istnieją brakujące source i apply
  contracts.
- Testy i evale skillów są coraz lepsze, ale następny poziom to użyteczność
  decyzji i adversarial overclaim prevention, nie tylko JSON shape, język
  polski i obecność evidence IDs.
- Knowledge cards i expert rules są dobrym fundamentem, ale nadal potrzebny
  jest knowledge compiler/source registry z freshness, confidence, lineage,
  owner review oraz dowodem, że reguły wpływają na decyzje.
- Największe ryzyko produktowe to mylenie gotowości demo z gotowością
  produkcyjną. Pre-demo gates dowodzą kształtu i core flow, nie marketer UAT
  ani agency-grade automation.

## Scorecard

To są interpretacje audytowe, nie twarde metryki:

- Solidne demo Ekologus: 72-82%.
- Realny boost marketera dziś: 60-70%.
- Content-generation workflow dla nowej strony: 55-65%.
- Pełny "lepszy BDOS" / agency-grade OS: 32-45%.

Interpretacja: WILQ jest już demoable, jeśli demo jest ustawione jako
review-first i evidence-backed. To nadal nie jest produkcyjny multi-client
optimizer, publishing engine ani write/apply automation platform.

## Kierunek Teraz

Nie dokładamy kolejnych szerokich powierzchni. Najbliższa praca powinna
udowodnić jeden mocny content workflow:

1. Zebrać source evidence z obecnych właściwości Ekologus: GSC, GA4, Ahrefs,
   Ads, Merchant, Localo i WordPress inventory.
2. Zmapować source evidence na aktualne URL-e oraz późniejszy target context
   dla `http://ekologus.dev.proudsite.pl/`.
3. Wykonać inventory, canonical i duplicate checks przed rekomendacją create.
4. Wygenerować polski brief lub plan draftu: source facts, angle, audience,
   objections, H1/H2/FAQ/CTA, internal links, missing evidence i forbidden
   claims.
5. Zostawić flow jako review-only do czasu validated ActionObject, preview,
   confirmation i audit path.
6. Wpiąć feedback marketera i post-publish performance z powrotem do
   knowledge, diagnostics i tactical queue.

## Zadania Do Rekonsyliacji Z Repo

Przed dodaniem któregokolwiek zadania uruchom checklistę Final A-Z z
`docs/goals/001-goal.md`. Dla każdego punktu najpierw sprawdź, czy już
istnieje, a potem oznacz jako `ready`, `hardening`, `task`, `blocked` albo
`deferred`.

### Demo Must-Haves

- Uruchomić lub potwierdzić najnowszy proof
  `scripts/pre_demo_gate.sh --core-skills` przed stakeholder demo.
- Przejść browser walkthrough z perspektywy marketera:
  `/command-center`, `/merchant`, `/content-planner`, `/ads-doctor`, `/ga4`,
  opcjonalnie `/localo`, `/actions/<key-action>`.
- Trzymać demo path jako wąski i jawnie review-only.
- Pokazać jeden konkretny content case z `act_prepare_content_refresh_queue`.
- Upewnić się, że prompt-to-Codex copy mapuje do właściwego skilla, endpointu,
  evidence IDs, ActionObject IDs i blocked claims.

### Content Workflow

- Zweryfikować, że `ekologus.dev.proudsite.pl` pozostaje typed target context,
  a nie niezależnym source evidence.
- Utwardzić old-to-new URL mapping, canonical checks i duplicate checks przed
  każdą rekomendacją create.
- Wzmacniać content brief/draft preview zamiast dodawać nowe powierzchnie.
- Dodać adversarial eval cases: BDO refresh, Zielony Ład merge/refresh, GA4
  `(not set)` jako blocker oraz Ahrefs gaps jako review input.

### Skills And Evals

- Dodać lub potwierdzić adversarial evale dla overclaimów: Ads CPA/ROAS/wasted
  budget, Merchant unique products/product ROAS, GA4 `(not set)`, Localo access
  proof vs metrics, Ahrefs uplift.
- Trzymać skill references jako guidance dla kontraktu i outputu. Product
  behavior należy do API/schema/view-model/expert rules/evals.
- Dodać human usefulness rubric: "czy marketer wie, co zrobić dalej?".

### API/Data Contracts

- Ads: target CPA/ROAS, business guardrails, change-impact windows, approved
  Keyword Planner enrichment i apply/audit contracts zostają deferred, chyba że
  zostaną wybrane jako aktywny slice.
- Merchant: unique product semantics, SKU/product IDs, historical price
  snapshots, before/after performance windows i feed write guards to głębsza
  praca, nie blocker demo.
- GA4: conversion/key event clarity istnieje jako read context, ale ROAS,
  profitability, conversion-drop i attribution verdicts pozostają blocked bez
  cost, history i attribution context.
- Localo: rankings/GBP/competitor/reviews mogą być read-only value, jeśli
  aktualne API evidence to potwierdza; local tasks, writes i uplift claims
  pozostają blocked.

### Dashboard UX

- Pierwsze ekrany mają być decision-first; raw/debug detale chowamy za
  drilldownem tam, gdzie to możliwe.
- "ActionObjecty" i raw payload language traktujemy jako operator/dev
  vocabulary. Marketer-facing copy powinno mówić np. "akcje do walidacji".
- Opportunities, Actions i Knowledge nie powinny być wejściem do demo, jeśli
  route nie odpowiada jasno: "co mam teraz zrobić i dlaczego?".

### Knowledge Compiler

- Zbudować source registry dla official docs, expert articles, benchmarks,
  decyzji marketera i historii kampanii.
- Dodać freshness, confidence, owner review, source lineage oraz
  superseded/stale states do promowanej wiedzy.
- Udowodnić, że knowledge cards wpływają na decyzje albo blokują unsafe claims
  zanim pokażemy je jako wartość produktową.

## Deferred BDOS Direction

Trzymać w archived BDOS backlog, chyba że zostaną jawnie promowane:

- Multi-client/account model.
- Production auth i permissions.
- Full write/apply mutation adapters.
- Monitoring, alerting i deployment hardening.
- Budget optimizer i multi-account Ads operations.
- Social publishing apply path.
- Localo/GBP write/uplift automation.

## Demo Framing

Bezpieczny claim:

> WILQ skraca dzienny review marketera, buduje evidence-backed content briefs
> i blokuje niebezpieczne wnioski.

Niebezpieczny claim:

> WILQ jest już pełnym BDOS, Ads optimizerem, feed repair systemem albo
> publishing engine.
