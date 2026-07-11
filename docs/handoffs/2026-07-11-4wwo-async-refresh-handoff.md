# Handoff — `wilq-seo-4wwo` async refresh

Data: 2026-07-11 19:35 Europe/Warsaw  
Ostatni commit: `ee53436` (`fix: respect connector refresh eligibility in dashboard`)  
`origin/main` = `ee53436`

## Wykonane

- `ConnectorRefreshRequest.run_async` jest opcjonalne i nie zmienia domyślnej
  ścieżki synchronicznej.
- Istniejący `POST /api/connectors/{connector}/refresh` zapisuje `queued`,
  background completion zapisuje `running`, a potem terminalny wynik.
- Istniejący `GET /api/connectors/refresh-runs/{run_id}` jest źródłem pollingu;
  dashboard `/settings` odpytuje go co 500 ms tylko dla `queued`/`running` i po
  zakończeniu unieważnia źródła, diagnostyki oraz command center.
- Drugi async request dla tego samego connectora zwraca istniejący aktywny
  run zamiast uruchamiać równoległy odczyt.
- `refresh_state.refresh_allowed` przechodzi na `false` dla aktywnego
  `queued`/`running` runu, więc status po przeładowaniu nie zachęca do drugiego
  odczytu.
- `/settings` używa `refresh_allowed` do warunkowego renderowania CTA; active-run
  test nie pozwala Reactowi pokazać drugiego odczytu.

## Dowody

- Backend: Ruff, mypy i `tests/api_contracts/test_connector_refresh_redaction_contracts.py` — 5 passed.
- Shared schemas: typecheck i 33 passed.
- Dashboard: typecheck, lint, build i focused refresh/active-run tests (2 passed) — green.
- Live API: `refresh_google_sheets_1204e9337620` zwrócił `queued`, następnie
  `completed`; `external_call_attempted=false`, bez vendor write.
- Browser proof typed state: `.local-lab/proof/4wwo-sources-refresh-state.png`
  oraz mobile variant.

## Nie robić ponownie

- Nie dodawać nowego endpointu ani osobnego translatora dla refresh statusu.
- Nie uruchamiać live refresh Google Ads/GA4/Merchant bez potrzeby; ich stan jest
  stale, a read-only refresh może być kosztowny lub zewnętrznie zablokowany.
- Nie włączać automatycznego stale-trigger tylko na podstawie tego slice’a.

## Następny slice

Zaprojektować i wdrożyć jawny API-owned kontrakt dla automatycznego triggera stale
źródeł: kwalifikacja decyzji, cooldown/rate-limit, backoff, audit i zachowanie
przy `partial`/`failed`. Deduplikacja aktywnego runu jest już wykonana, więc
następna praca nie powinna jej powtarzać. Jeśli kontrakt wymaga danych, najpierw
zostawić auto-trigger wyłączony i opisać blocker; `r564.3` nadal jest blokowany
przez brak świeżego, actionable kandydata contentowego.

Niezależny następny seam roadmapy został wykonany w `jnra`: projekcje historii
audytu przeniesiono do `wilq/actions/audit_store.py`. Nie wracaj do tego seamu;
następny refaktor `service.py` musi wybierać inną potwierdzoną granicę.

## Kontrola repo

- Ostatni push: `origin/main` wskazuje `3771c02` przed bieżącym commitem docs.
- Worktree po commicie powinien być czysty; przed następnym slice’em sprawdź
  `rtk git status --short`, `rtk bd ready --json` i health API.
