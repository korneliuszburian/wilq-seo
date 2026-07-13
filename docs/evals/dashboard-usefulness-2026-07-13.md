# Dashboard usefulness review — 2026-07-13

## Zakres i metoda

Fresh packet: `.local-lab/proof/dashboard-second-opinion/2026-07-13/`.
Oceniono screenshot desktop 1440×1024 i mobile 390×844, najpierw marketer
mode, potem technical audit mode. Kryteria 0–10: (1) decyzja w 30 s, (2)
powód i blocker, (3) evidence/freshness bez technicznego payloadu, (4) jeden
bezpieczny następny krok, (5) brak card slop/mobile overflow. To jest review
operatora na renderze, nie wynik testu DOM.

## Wynik

| Surface | Score | Co działa | Następny tuning |
| --- | ---: | --- | --- |
| `/command-center` desktop/mobile | 7/10 | priorytet i blokery są widoczne; dane są świeże z live WILQ | skrócić listę do jednej najlepszej pracy i jednego CTA |
| `/content-workflow` marketer | 8/10 | public URL, decyzja, blocker, freshness, dev preview i „nic nie zostanie opublikowane” są above the fold | zmniejszyć ciężar sekcji statusów przy dłuższym scrollu |
| `/content-workflow` technical audit | 8/10 | przełącznik odsłania dowody/kontrakty/ślad bez mieszania z marketer view | nazwać techniczne sekcje według celu debugowania, nie mechanizmu |
| `/opportunities` / `Kolejka` | 7/10 | jedna canonical queue łączy opportunities i actions | pokazać jawnie filtr gotowe/zablokowane/review na pierwszym ekranie |
| `/content-workflow` mobile | 7/10 | tryb marketer i CTA są dostępne bez poziomego overflow | skrócić pionowy blok źródeł przed edytorem sekcji |

## Live API context

- health: `ok`
- metric facts: `104362`
- refresh runs: `4580`
- content queue: `2` candidates, blocker `not_enough_actionable_candidates`
- snapshot homepage: freshness `fresh`, public canonical
  `https://www.ekologus.pl/`, evidence IDs z GSC i WordPress

## Werdykt

Kierunek utrzymać. WILQ jest już wyraźnie bliżej operating cockpit niż zwykły
prompt, bo decyzja jest powiązana z aktualnym URL, źródłami, blockerem i
bezpiecznym krokiem, a technical mode nie zatruwa pierwszego widoku. Nie jest
jeszcze BDOS-class: kolejka contentowa ma za mało actionable tematów, a
command center nadal agreguje zbyt wiele równorzędnych powierzchni.

## Najbliższy test

Sprawdzić, czy filtracja canonical queue i mobile triage skraca drogę od blokady
do odświeżenia źródła. Nie dodawać nowych kart bez dowodu, że poprawiają wynik
30-sekundowego zadania.
