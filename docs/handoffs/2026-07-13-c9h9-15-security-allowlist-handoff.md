# Handoff — 2026-07-13: scoped detect-secrets allowlist

## Domknięty slice

`wilq-seo-c9h9.15` usuwa fałszywy alarm `detect-secrets` dla kontrolowanej
fixture redakcji w `tests/actions/test_audit_store_contracts.py`. Jedyna zmiana
w fixture to inline `# pragma: allowlist secret` przy dokładnie tej fizycznej
linii; produkcyjna redakcja i globalne pluginy skanera nie zostały osłabione.

## Dowód

- Przed zmianą scoped scan fixture wskazywał jeden `Secret Keyword` na linii
  fixture.
- Po zmianie zwykły scoped scan ma zero wyników, a `--only-allowlisted` zwraca
  dokładnie jeden `Secret Keyword`.
- `tests/test_security_detect_secrets_allowlist.py` sprawdza, że identyczny
  nieallowlistowany klucz w innym pliku tymczasowym nadal jest wykrywany oraz
  że `scripts/security.sh` nadal skanuje całe repo bez wykluczenia fixture.
- Focused pytest: 14 passed; Ruff i mypy przechodzą.
- Pełny `scripts/security.sh`: detect-secrets `{}`, pip-audit bez znanych
  podatności. Semgrep jest niedostępny i skrypt zgłasza to jawnie.

## Caveat

Pragma tłumi wszystkie findingi na tej jednej linii. Nie dopisuj na niej
rzeczywistych credentiali ani nie rozszerzaj pragma na plik lub globalne
exclude rules.

## Następny slice

Wybierz z bieżącego `bd ready`: produktowa kolejka contentowa nadal nie może
udawać trzeciego evidence-backed tematu, a niezależne techniczne seamy to
`c9h9.16` (snapshot API) i `c9h9.18` (tactical Ahrefs extraction). Nie wracaj
do tego allowlist worku bez nowego wyniku skanu.
