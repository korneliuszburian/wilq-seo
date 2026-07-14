# Handoff — `inoz` daily-check readiness — 2026-07-13

## Decyzja

`wilq-seo-inoz` można zamknąć. Pierwszy request po readiness nie czeka na
niegotowy runtime: zwraca typed `daily_check_runtime_prewarm`. Po zakończeniu
prewarmu pełny daily-check mieści się w budżecie i nie buduje już niepotrzebnie
pełnego `DailyRuntimeBase` ani marketing brief. Pobiera jednak kanoniczne action
inventory: warm `list_actions_cached()` przy zwykłym odczycie albo świeże
`list_actions()` przy `use_cache=false`. Jeden reentrant lock obejmuje kompozycję runtime,
cache write i invalidację, więc równoległe cold missy nie dublują builda, a
`clear()` nie pozwala staremu wynikowi wrócić do cache.

## Minimalna zmiana

- `build_daily_check_runtime()` używa istniejącej lekkiej ścieżki
  `build_daily_command_center()`.
- Lista connectorów pochodzi z typed `CommandCenterResponse.connector_health`.
- Lekki Command Center i pełny runtime używają tego samego providera action
  inventory. Test `light prewarm -> full cached -> full uncached` wymaga tej
  samej dostępności akcji i nie pozwala wrócić do bezwarunkowych stubów.
- Focused test zabrania wywołania pełnego `build_daily_runtime_base()` i
  marketing brief w daily-check runtime.
- Command Center po cold miss ponownie sprawdza cache pod wspólnym lockiem.
  Focused concurrency test wymusza dwa równoległe missy i oczekuje jednego
  builda; drugi test rozpoczyna invalidację podczas builda i wymaga nowego
  snapshotu przy następnym odczycie.

## Proof

- Przed zmianą kontrolowany Command Center cold read trwał `3.805070 s`, a
  daily-check wykonany zaraz po nim nadal `5.616012 s`, bo osobno budował pełny
  base/actions.
- Po managed restart trzy szybkie odczyty podczas prewarmu zwróciły wyłącznie
  blocker `daily_check_runtime_prewarm` w
  `0.016174/0.049694/0.059211 s`.
- Po prewarmie trzy pełne odczyty trwały
  `0.031437/0.014504/0.016272 s`: status `blocked` wynika z realnego review GA4,
  a wynik zachowuje freshness, 23 evidence IDs, 7 source connectors i 3 safe
  next actions.
- Finalny review wykrył, że wcześniejszy light builder wkładał do wspólnego
  cache'u stuby, m.in. nieistniejącą w registry akcję Ads. Po naprawie managed
  restart i warm proof dały `0.022014 s` dla daily-check oraz `0.004116 s` dla
  Command Center, a focused test chroni niezależność wyniku od kolejności.
- Focused daily lifecycle/GA4/Command Center gate, Ruff i standalone facade
  mypy przechodzą. Finalne `scripts/verify.sh`: 929 backend tests + 2 skips, 157
  dashboard tests, API/skill smokes, 19/19 Playwright i production build.
- Mutation readiness: 21 akcji, `vendor_write_possible_count=0` i
  `would_attempt_vendor_write_count=0`.
- Browser `/command-center` pokazuje priorytet Merchant, kolejkę Treści/Ads oraz
  jawną blokadę GA4; proof:
  `.local-lab/proof/inoz-daily-check-readiness-20260713/command-center-final.png`.

## Odrębne ryzyko

Nie mylić zamkniętego startup race z późniejszym expiry spike. Kontrolowany
idle proof wykazał serię `12.973748/4.546343/2.714065 s`, potem warm hits około
`0.015 s`. Profil na kopii store mierzy osobno: Command Center `3.888417 s`,
GA4 `4.618954 s`, content diagnostics `4.355917 s`. Ten problem ma własny bead
`wilq-seo-3bnt`; nie podnosić TTL bez dowodu freshness/invalidation.
