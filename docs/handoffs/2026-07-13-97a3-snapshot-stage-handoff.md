# Handoff — `wilq-seo-97a3`

## Decyzja

Wydzielono snapshot stage adapters i helpery przygotowania stanu z
`wilq/content/workflow/api.py` do `stage_snapshot.py`. API zachowuje istniejące
kontrakty i używa typed `SnapshotStageCallbacks`; nie dodano endpointu i nie
odblokowano WordPress writes/publish.

## Dowody

- `api.py`: 868 → 644 LOC; changed-code complexity violations: 0.
- Focused content workflow contract/end-to-end/adversarial suite: passed.
- Ruff, mypy i `git diff --check`: passed.
- Live API: health `ok`; queue ma 2 kandydatów i blokadę
  `not_enough_actionable_candidates`; homepage snapshot ma `fresh`, public
  canonical `https://www.ekologus.pl/`, 2 evidence IDs oraz konektory GSC i
  WordPress.
- Browser `/content-workflow`: decyzja usługi, public/dev sections, editor,
  preview CTA i ActionObject safety blocker są widoczne; szczegóły techniczne
  pozostają w disclosure.

## Następny krok

Ponownie odczytaj `bd ready`, complexity i live API. Nie powtarzaj snapshot
seamu. Wybierz kolejny potwierdzony blocker/operator seam; writes nadal muszą
przechodzić przez centralny ActionObject.
