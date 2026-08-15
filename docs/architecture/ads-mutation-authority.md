# Proponowany autorytet mutacji Google Ads

Rola: `decision record` (ADR). Dokument jest rekomendacją przygotowaną do
decyzji `OWNER`; ma status **PROPOSED / oczekuje na zatwierdzenie**. Nie
autoryzuje żadnego vendor write, nie zmienia kodu i nie decyduje o przyszłym
adapterze. Bead: `wilq-seo-v9ab.17.8`.

## Stan dzisiejszy (dowody)

- WILQ nie ma adaptera mutacji Google Ads. Każda akcja Ads jest
  **prepare-only**: `mode=prepare_only`, `apply_allowed=False`
  (np. `wilq/actions/google_ads/demand_gen.py:403-425`).
- ActionObject lifecycle (`validate → preview → review → confirm → impact →
  apply → audit`) istnieje i jest używany dla WordPress draft-only;
  **nie ma ścieżki apply dla Ads**.
- Zewnętrzny natywny Google Ads pozostaje granicą wykonania: marketer wykonuje
  zmianę ręcznie w UI Google po read-only diagnozie WILQ.

## Do rozstrzygnięcia przez OWNER-a

Pytanie produktowe, nie implementacyjne:

- **Opcja A — natywny Google Ads pozostaje stałą granicą wykonania.**
  WILQ diagnozuje i przygotowuje review-only akcje; każdą mutację wykonuje
  Wilku ręcznie w Google Ads. `apply_allowed` pozostaje `false` na stałe dla
  Ads, a skille nie obiecują wykonania.
- **Opcja B — oddzielnie scoped bounded adapter pilot.**
  WILQ zyskuje adapter mutacji Ads dla **dokładnie wymienionych operacji**
  (np. negative keywords, pause, budget), przez pełny ActionObject
  preview→review→confirm→audit, z least-privilege i rollback proof.
  Wymaga osobnej autoryzacji, dokładnej listy operacji i dowodu
  auditability/rollback. Do tego czasu `apply_allowed` pozostaje `false`.

## Kryteria oceny (do decyzji)

| Kryterium | Opcja A | Opcja B |
| --- | --- | --- |
| Ryzyko | niskie — brak vendor write | średnie/wysokie — realny write |
| Auditability | zewnętrzna (Google UI) | wewnętrzna (ActionObject + audit) |
| Rollback | manualny w Google Ads | wymaga proofu i least-privilege |
| Wartość dla marketera | niska (ręczna robota) | wysoka (execution w WILQ) |
| Koszt utrzymania | brak | adapter + auth + testy + runbook |

## Rekomendacja do zatwierdzenia

Rekomendowany domyślny kierunek to **A — natywny Google Ads pozostaje granicą
wykonania** na razie, z jawną decyzją, że WILQ nie udaje mutacji. **B** to
osobny, świadomie scoped eksperyment, który wymaga dokładnej listy operacji,
autoryzacji i proofu — bez tego `apply_allowed` pozostaje `false` i żaden skill
nie obiecuje wykonania.

## Oczekująca decyzja OWNER-a

- **P1 — granica:** A (natywny UI na stałe) albo B (bounded adapter pilot).
- **P2 — zakres B (jeśli B):** dokładna lista operacji, uprawnienia
  (least-privilege), środowiska, rollback proof, runbook.
- **P3 — komunikacja:** czy skille mają jawnie deklarować `apply_allowed=false`
  dla Ads (dzisiejszy stan) bez zmian.

Do czasu rozstrzygnięcia P1–P3 żadna mutacja Ads nie jest autoryzowana;
`apply_allowed` pozostaje `false`, a WILQ nie wykonuje vendor write.
