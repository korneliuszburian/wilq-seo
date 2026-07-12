# Handoff — nlax content activation helpers — 2026-07-13

## Decyzja

WordPress draft readback oraz activation label/checklist helpers zostały
wydzielone do `wilq/content/workflow/stage_activation.py`. Activation wrapper
korzysta teraz z jednego typed ownera, bez duplikacji i bez zmiany kontraktu.

## Dowody

- Focused activation/readiness tests: passed.
- Ruff, mypy i `git diff --check`: passed.
- Complexity extraction-only report: `api.py` 1148 → 1017 LOC; residual
  file-budget violation pozostaje jawny.
- Live po managed restart: `workflow_snapshot`, freshness `fresh`, 2 evidence
  IDs GSC/WordPress, 1 handoff blocker.
- Browser `/content-workflow`: public URL, decision, blocker i draft-only CTA
  pozostają widoczne.

## Następny zakres

`wilq-seo-b0ja` obejmuje pozostałe write-readiness/audit orchestration. Nie
odblokowywać live write ani publish.
