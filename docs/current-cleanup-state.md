# Current cleanup state — navigation

Stan na: 2026-09-11. Rola dokumentu: `current-state` dla higieny repozytorium,
nie drugi dziennik produktu ani źródło per-URL statusu.

Źródła prawdy są rozdzielone:

- `PLANS.md` — bieżący plan, bramy i znane ograniczenia;
- aktywny Bead — jeden executable slice, WIP i proof;
- `docs/content-status-214.csv` — jedyny kanoniczny journal 214 URL-i;
- WILQ API/SQLite — evidence, revisions, reviews, mappings, ActionObjects i
  readbacki;
- git/closed Beads — historia, nie bieżący stan.

Ostatni stan cleanupu:

- dirty checkout został zintegrowany z `origin/main`; validator hardening jest
  w `115407d9`, a cleanup/navigation w `93069e76`; bieżąca gałąź jest czysta po
  synchronizacji Beads;
- niezarządzany Vite na `127.0.0.1:37621` został zatrzymany po potwierdzeniu,
  że canonical managed stack działa na API `8000` i dashboardzie `5173`;
- worktrees z nie-scalonymi gałęziami są zachowane do osobnej decyzji; sama
  nazwa ani wiek gałęzi nie jest dowodem, że można ją porzucić;
- historyczne snapshoty i runy pozostają oznaczone jako `historical/reference`
  albo forensic evidence, dopóki ich consumer, supersession i retention nie są
  jawnie rozstrzygnięte.

Reguła cleanupu: najpierw read-only inventory i `rg` referencji, potem jeden
recoverable krok dla potwierdzonego artefaktu; nie naruszać credentials, `.env`,
SQLite, Beads, canonical CSV, evidence lineage ani plików używanych przez CI i
managed runtime. Po każdym kroku wymagane są `git diff --check` oraz właściwy
focused proof. Publiczne WordPress publish/update/delete pozostają poza zakresem.

Następny krok jest w aktywnym Beadzie `wilq-seo-1oa.36.116`: dokończyć mapę
referencji i dopiero na jej podstawie rozstrzygnąć, które stare dokumenty,
artefakty i worktrees są rzeczywiście superseded.
