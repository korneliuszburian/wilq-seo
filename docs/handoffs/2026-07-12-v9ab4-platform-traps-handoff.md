# Handoff — `v9ab.4` platform-trap rule packs

Data: 2026-07-12 Europe/Warsaw

## Decyzja

Domknięto `wilq-seo-v9ab.4` jako najmniejszy produktowy slice po rebaseline.
WILQ nie oznacza już tylko całej domeny jako `platform_trap`; ma typed
`PlatformTrapContract` z ograniczeniami, blokowanymi wnioskami i bezpiecznymi
następnymi krokami.

## Wykonane

- Dodano pięć rule packów:
  `ads_platform_traps_v1`, `ga4_platform_traps_v1`,
  `merchant_platform_traps_v1`, `gsc_platform_traps_v1` i
  `wordpress_platform_traps_v1`.
- Każdy pack ma source ID z istniejącego registry i minimum trzy constraints
  oraz dwa safe next steps.
- Istniejące `/api/expert/rules`, `/api/expert/rule-summaries` i
  `/api/expert/sources` zostały rozszerzone bez nowego endpointu.
- Ads, GA4 i Merchant diagnostics odwołują się do platform trap IDs; WordPress
  pack jest gotowy do użycia przez istniejący registry i następne decyzje
  contentowe.
- Nie zmieniono ActionObject write flow, vendor adapters ani dashboard business
  logic.

## Dowody

- Focused/full contract suites dla expert rules, Ads, GA4, Merchant i source
  diagnostics przechodzą.
- Ruff, mypy i `git diff --check` przechodzą.
- Live API po managed restart: `/api/health` `ok`; `/api/metrics/status`
  raportuje 98 915 facts i 4 572 refresh runs.
- Live `/api/expert/rules` zwraca pięć trap contracts z source IDs; Merchant
  decision queue zwraca `merchant_platform_traps_v1`.
- Browser proof: `.local-lab/proof/platform-trap-merchant-first-viewport.png`;
  pierwszy viewport pokazuje świeżość, blocker i bezpieczny refresh/review bez
  automatycznego zapisu.

## Nie robić ponownie

- Nie dodawać drugiego expert endpointu ani kopiować trapów do skill references.
- Nie traktować platform trap jako dowodu metryk; nadal potrzebne są evidence IDs,
  source connectors i freshness z WILQ API.
- Nie włączać write/publish na podstawie samego `platform_trap`.

## Następny slice

Po zamknięciu tego Beada odblokowuje się `wilq-seo-v9ab.5`: typed ExpertRule
conditions, required connectors/metrics/windows, false-positive checks,
blocked states i safe recommendation contract. Najpierw sprawdź aktualny
schema/API i nie powielaj już istniejącego `PlatformTrapContract`.

## Repo

Po aktualizacji Beads wykonaj commit, push na `origin/main`, sprawdź zgodność
`HEAD`/`origin/main` i zostaw worktree czysty przed następnym slice’em.
