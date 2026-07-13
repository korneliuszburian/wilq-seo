# WILQ target visualization brief — 2026-07-13

Ten brief jest źródłem dla kolejnego roastu/design prototype. Opiera się tylko
na istniejących, sprawdzonych powierzchniach WILQ; nie projektuje fikcyjnych
metryk, endpointów ani write actions.

## Rola produktu

WILQ to marketer-first, evidence-first Marketing Operating System dla polskiego
operatora Ekologus. Pierwszy ekran ma odpowiedzieć w 30 sekund:

1. Co zrobić teraz?
2. Dlaczego ta praca ma znaczenie?
3. Jakie dowody i świeżość to wspierają?
4. Co ją blokuje?
5. Jaki jest następny bezpieczny krok?

## Nawigacja

Primary marketer nav: `Dzisiaj`, `Kolejka`, `Treści i SEO`, `Reklamy i pomiar`,
`Produkty`, `Lokalnie`, `Akcje`.

Secondary/admin: `Procesy`, `GA4`, `Wiedza`, `Źródła`.

Technical/audit: raw evidence IDs, ActionObject, contracts, runtime logs,
payload previews and connector internals. Nie mogą być równorzędnymi kartami w
primary nav.

## Daily cockpit

Pierwszy viewport `/command-center`:

- jedna karta „Następna najlepsza praca” z tytułem, powodem, dowodem, blockerem
  i CTA;
- kompaktowa lista najwyżej kilku kolejnych decyzji;
- źródła/freshness jako krótki status, nie dashboard metryk;
- zakazane twierdzenia i blokady obok decyzji;
- technical details w disclosure.

Na mobile: jedna praca, dwa blokery, jedno CTA. Nie renderować równorzędnych
paneli przed wykonaniem pierwszej decyzji.

## Content workflow

`/content-workflow` jest główną trasą pracy nad jedną publiczną stroną:

- public canonical `ekologus.pl` jako SEO truth;
- dev WordPress wyłącznie jako workspace draftów;
- aktualne sekcje, GSC/WordPress/Ahrefs signals, freshness i Service Profile;
- decyzja `zachowaj / odśwież / scal / utwórz / zablokuj`;
- claim/evidence summary i jeden safe next step;
- marketer mode domyślnie;
- technical audit mode dopiero po świadomym przełączeniu;
- current vs proposed i preview, bez automatycznej publikacji.

## Diagnostic screen

Każdy diagnostic surface powinien mieć tę samą hierarchię:

1. decyzja i jej konsekwencja dla operatora;
2. najważniejszy blocker;
3. dowód/freshness/source summary;
4. bezpieczne działanie review-only;
5. technical disclosure.

Realne źródła WILQ obejmują Ads, GA4, GSC, Merchant, Localo, Ahrefs,
WordPress, knowledge cards i ActionObject readiness. Brak kontraktu blokuje
wniosek zamiast tworzyć placeholder metric.

## Workflow i safety

Content workflow: preflight → Sales Brief → Claim Ledger → draft package →
quality review → human review → WordPress draft-only → measurement window.

Każdy write: validate → preview → human review → confirm → audit → vendor
adapter. `apply=false`, publikacja i destructive update pozostają jawnie
zablokowane, jeśli adapter/kontrakt nie istnieje.

## Design test

Reviewer ma ocenić render 0–10 według: decyzja w 30 s, blocker, evidence/
freshness, jeden CTA, cognitive load/mobile overflow. Nie używać automatycznego
10/10 jako dowodu. Aktualny packet: `.local-lab/proof/dashboard-second-opinion/2026-07-13/`.
