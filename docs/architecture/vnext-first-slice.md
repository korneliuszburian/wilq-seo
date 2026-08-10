# vNext first slice — read-only PageMaterial + create-only `the_content` draft

Rola dokumentu: `reference`. Stan na: 2026-08-07, fixed point `a783efe0`.
Jest to rekomendacja pierwszej małej, wykonywalnej pracy vNext. Nie uprawnia do
vendor write poza już istniejącą create-only granicą dev draftów.

## Cel slice'a

Domknąć jeden pełny workflow od źródła do dev preview w najprostszy możliwy
sposób, bez przebudowy storage i bez ACF write:

```text
read-only WordPress source inventory + PageMaterial snapshot
  → native the_content full-document revision
  → human review
  → ActionObject create-only draft on dev
  → exact REST readback + preview
```

Dodatkowo: **read-only ACF discovery** dla wybranego work itema, żeby następny
slice (ACF write) pracował na prawdziwej strukturze, a nie na domyśle.

## Dlaczego ten slice jest pierwszy

1. Wszystkie elementy już istnieją i są przetestowane (BDO `1932`, KIP `1934`,
   Ocena środowiskowa `1933` udowodniły create-only dev draft + readback).
2. Nie zmienia storage, nie dodaje nowego frameworku, nie tworzy nowych
   odpowiedzialności — najwyższa wartość przy minimalnym ryzyku.
3. Definiuje `PageMaterial` w praktyce (source identity, rendering surface,
   struktura, evidence) zanim zapadnie decyzja o migracji storage.
4. Read-only ACF discovery daje prawdziwą strukturę dla slice 2.

## Kontrakt slice'a (caller → public seam → observable result)

| Krok | Seam | Observable result |
| --- | --- | --- |
| 1. Read-only source inventory | `refresh_wordpress_content_inventory` / `read_wordpress_content_material` (read-only) | jeden canonical URL + object type/id + source revision + `the_content` (lub ACF) |
| 2. PageMaterial snapshot | nowy read-only view model `PageMaterial` (digesty, surface enum, struktura, evidence `used|missing|not_matched`) | marketer widzi pełny materiał strony w <30s |
| 3. Full-document revision | `POST /api/content/work-items/{id}/initial-draft` → `ContentDraftRevision` (append-only) | kompletny dokument z section IDs, claims, CTA |
| 4. Human review | `POST /api/content/work-items/{id}/draft-revisions/{rev}/review` (exact digest) | `approved` z exact revision+digest |
| 5. Create-only ActionObject | `target-mapping/confirmation` + `target-mapping/draft-action` → ActionObject | jedna akcja z binding, gate human |
| 6. Apply → dev draft | ActionObject lifecycle → `create_wordpress_draft_post` (dev only) | nowy draft na `ekologus.dev.proudsite.pl`, źródło nietknięte |
| 7. Exact readback + preview | `wordpress_draft_readback` (status/title/link/edit_link/modified/content) | podgląd szkicu w dashboardzie |
| 8. Read-only ACF discovery (obok) | `build_wordpress_authoring_profile` + `read_wordpress_acf_rest_schema` + `read_wordpress_acf_flexible_snapshot` — tylko identity + digesty | mapa layoutów/pól/order dla pracy nad ACF w slice 2 |

## Granice slice'a (nie rób w tym slice)

- **Zero pełnego ACF write** — ACF discovery tylko read-only.
- **Zero migracji storage** — żadnych nowych tabel/kolumn poza ew. read-only
  view model (jeśli wymaga rekordu → osobny slice 2).
- **Zero nowych vendor write** — wyłącznie istniejąca create-only granica.
- **Nie naprawiaj GA4/Ahrefs/Ads decision rules** — tylko dokumentuj stan.
- **Nie usuwaj legacy** — legacy cleanup to osobny slice.

## Kryteria ukończenia (falsifiery)

1. Wybrana strona `the_content` (np. ponowne użycie istniejącego work itema bez
   tworzenia drugiego draftu — jeden draft na rewizję) przechodzi cały łańcuch.
2. Readback zwraca `modified_gmt` + content summary + status `draft`; źródłowy
   obiekt niezmieniony.
3. `PageMaterial` snapshot pokazuje: canonical URL, object type/id, rendering
   surface, strukturę, digesty, evidence `used|missing|not_matched` — bez
   żadnych wartości sekretów.
4. ACF discovery dla wybranej strony z ACF zwraca layouty, sibling fields,
   `root_digest`, `fields_digest`, order — bez persisted raw payloadu.
5. Żaden nowy endpoint nie pozwala na publish/update/delete/force-delete.
6. `scripts/lint.sh` i `scripts/typecheck.sh` zielone; skupione testy content
   zielone.

## Dowód, który slice ma zostawić

- Zapisany wynik: `PageMaterial` snapshot + revision + review + ActionObject
  id + dev draft id + readback.
- Bead (istniejący tracker) z właścicielem, dowodem i next action.
- Commit/push osobno od tej analizy — po decyzji ownera.

## Następny slice (2) — w skrócie

- Uporządkować `PageMaterial` jako canonical record (decyzja z §12 pkt 5).
- ACF write przez istniejący `ContentAcfClonePlan` — dopiero po potwierdzeniu
  struktury z slice 1 i naprawie post-create readback digest (slice 3).
