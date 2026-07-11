# Handoff — `jnra` audit history seam

Data: 2026-07-11 19:45 Europe/Warsaw  
Ostatni commit: `d60593b` (`docs: point handoff to latest cleanup commit`)  
`origin/main` = `d60593b`

## Wykonane

- Read-only projekcje audytów akcji i mutation auditów zostały przeniesione z
  `wilq/actions/service.py` do `wilq/actions/audit_store.py`.
- Projekcje filtrują po `action_id`, utrzymują maksymalnie 10 wpisów na akcję i
  zachowują puste mapy dla żądanych identyfikatorów bez historii.
- `service.py` importuje kompatybilne aliasy; validate → preview → review →
  confirm → audit → adapter nie zmienił semantyki.

## Dowody

- `tests/actions/test_audit_store_contracts.py` oraz action review/evidence/
  validation contracts: 9 passed.
- Ruff, mypy, `scripts/audit_complexity.py --changed --allow-frozen
  --allow-budget-violations` i `git diff --check` przechodzą.
- Complexity po seamie: 394 pliki Python, 132243 non-empty LOC,
  `wilq/actions/service.py` 4224 LOC; raport nadal wskazuje zamrożony budżet
  service.py jako znane tło większego Beada, bez wzrostu funkcjonalnego.

## Nie robić ponownie

- Nie przenosić ponownie projekcji audytów ani zmieniać limitu 10 bez nowego
  dowodu kontraktowego.
- Nie dotykać ActionObject write gates w ramach refaktoru storage projection.

## Następny slice

`wilq-seo-kgvy`: wybrać jeden niezależny builder z `ads_diagnostics.py`, przenieść
go do istniejącego lub nowego modułu domenowego, zachować evidence IDs, source
connectors, blocked CPA/ROAS/waste claims i stabilny response contract. Najpierw
sprawdzić aktualne funkcje i testy; nie powtarzać już wyekstrahowanych section/
decision builders.

## Kontrola repo

- `HEAD == origin/main == d60593b`.
- Worktree po commicie jest czysty; przed kolejnym slice’em sprawdź `rtk git
  status --short`, `rtk bd ready --json` i health API.
