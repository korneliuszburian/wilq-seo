# Handoff — c9h9.16 content snapshot seam — 2026-07-13

## Decyzja

Orchestracja snapshotu `/content-workflow` została wydzielona do
`wilq/content/workflow/snapshot_assembly.py`. Moduł ma typed input/output i
`SnapshotAssemblyCallbacks`; API zachowuje routing oraz stage-specific builders
jako adaptery. Nie zmieniono endpointów, claim rules ani write path.

## Dowody

- Focused content contracts: 12 passed.
- Ruff, mypy i `git diff --check`: passed.
- Complexity extraction-only report: `api.py` spadł do 1470 LOC; pozostałe
  file-budget violation jest jawne, bez maskowania.
- Live after managed restart: snapshot `workflow_snapshot`, freshness `fresh`,
  2 evidence IDs z `google_search_console` i `wordpress_ekologus`;
  Service Profile review-required, handoff blocker 1, measurement blocker 1.
- Browser proof: `/content-workflow` pierwszy viewport pokazuje publiczny URL,
  decyzję usługi, blocker i CTA draft-only; techniczne szczegóły są niżej.

## Pozostały zakres

Stage callbacks nadal są lokalnymi adapterami w `api.py`. Kolejny extraction
może przenieść ich typed builders dopiero po osobnym dowodzie; nie wracaj do
tego seamu ani nie dodawaj nowego endpointu.
