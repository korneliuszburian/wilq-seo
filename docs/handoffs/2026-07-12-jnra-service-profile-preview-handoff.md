# Handoff: `jnra` Service Profile preview cards — 2026-07-12

## Decyzja

Przeniosłem dwa istniejące renderery kart z `wilq/actions/service.py` do
`wilq/actions/service_profile.py`: publiczny knowledge-promotion oraz redacted
private-proposal promotion. Service zachowuje dispatcher i przekazuje callbacks
do typed rows, list oraz safety labels. Nie dodano endpointu ani capability zapisu.

## Dowód produktu

- Live API: oba endpointy zwróciły HTTP 200, `mode=prepare`, connector
  `wordpress_ekologus`, evidence `ev_content_service_profile_source_facts` i
  właściwe typed card kinds.
- Publiczna karta zachowuje source facts, public source, review role, blocked
  claims oraz `apply_allowed=false`.
- Prywatna karta zachowuje redacted marker bez raw private text, review role,
  freshness/access rows, blocked claims oraz `apply_allowed=false`.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/service-profile-private-preview-live.png`.

## Weryfikacja

- `tests/content/test_content_knowledge_cards.py -k 'promotion_action or preview'`
  i Service Profile API contracts: passed.
- Ruff i mypy dla `service.py` oraz `service_profile.py`: passed.
- Complexity changed audit: brak nowych naruszeń modułu; znany frozen budget
  `service.py` pozostaje jedynym findingiem.
- `git diff --check`: passed.
- Managed stack po restarcie: API/dashboard ready; health `ok`.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; seam jest bounded i nie duplikuje
  istniejącego zadania.
- `wilq-seo-r564` pozostaje zewnętrznie zablokowany kolejką contentu: 1
  actionable przy minimum 3.
- Następny turn wybiera kolejny istniejący preview/action seam po świeżym
  complexity i runtime checku; nie wraca do ukończonych rendererów.

## Commit

Commit implementacji i docs zostanie dopisany po pushu.
