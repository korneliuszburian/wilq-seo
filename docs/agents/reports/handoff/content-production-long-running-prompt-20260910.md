# Handoff: pełna produkcja treści i SEO Ekologus

Rola: `current handoff` dla kolejnej instancji Codex. Konsument: następna,
tańsza instancja kontynuująca aktywny goal. Ten dokument nie zastępuje Beads,
`PLANS.md` ani `docs/content-status-214.csv` i nie dowodzi ukończenia.

## Prompt do wklejenia

```text
Pracujesz autonomicznie w repozytorium:
/mnt/storage/coding/krn/active/wilq-seo

Masz doprowadzić do końca aktywny, długotrwały program evidence-bound produkcji
wszystkich treści i SEO dla ekologus.dev.proudsite.pl. Nie kończ na audycie,
planie, prototypie ani częściowym pipeline. Jesteś jedynym operatorem repo:
odpowiadasz za kod, research, treści, review, Beads, commity, PR-y, merge,
porządek checkoutów i managed runtime. Niezależni sędziowie są odizolowanymi,
read-only agentami/modelami, a nie ludźmi, na których można czekać.

Najpierw przeczytaj w całości najbliższy AGENTS.md, potem:
1. bd prime
2. bd list --status=in_progress --json
3. bd show wilq-seo-1oa.36.101
4. PLANS.md
5. docs/CONTEXT.md
6. docs/content-status-214.csv
7. docs/agents/issue-tracker.md, delivery.md, review.md i artifacts.md

Nie twórz nowego celu, drugiego journalu ani Markdown TODO. Beads jest jedyną
kolejką. docs/content-status-214.csv jest jedynym kanonicznym per-URL journalem.
Dokładnie jeden implementation Bead może być in_progress. Jeden slice ma jednego
writera w osobnym czystym worktree, jeden observable result, focused falsifier,
fixed-point Spec+Standards review i jeden cohesive commit. Research/review mogą
działać równolegle wyłącznie read-only. Implementacji nie prowadź w brudnym
głównym checkoutcie.

Stan wejściowy, który musisz zweryfikować zamiast zakładać:
- S0 jest scalony przez PR #80 jako merge 530c6094; CI run 34471087695 był
  zielony we wszystkich trzech jobach.
- S0 ustanowił canonical CSV authority, odciął historyczny Wave0 od current
  consumers i zachował go tylko jako explicit historical read.
- jedyny aktywny Bead: wilq-seo-1oa.36.101 (S1 exact delivery identity).
- worktree S1:
  /mnt/storage/krn/worktrees/wilq-content-production-s1
  branch agent/content-production-s1, base 530c6094.
- finalny S1 fixed point: `222af033fee6137cce1fa0c68f67160345cc38a5`.
- Spec review: PASS; Standards review: PASS. Final proof: 49 targeted tests,
  Ruff, mypy, Bandit i diff-check PASS; complexity 0.
- branch został pushnięty, a PR #81 jest otwarty:
  https://github.com/korneliuszburian/wilq-seo/pull/81
- PR head musi pozostać dokładnie `222af033`; CI mogło jeszcze trwać w chwili
  handoffu. Nie powtarzaj implementacji ani review bez zmiany fixed pointu.

Pierwsza akcja:
1. Sprawdź PR #81 i potwierdź head `222af033`; poll konkretnego CI runu.
2. Jeśli CI jest red, diagnozuj log i wróć do tego samego S1 worktree; nie rób
   ślepego rerun. Zmieniony fixed point wymaga ponownego Spec+Standards review.
3. Jeśli wszystkie wymagane joby są zielone, merge PR #81, zweryfikuj merge SHA
   i ancestry, zapisz proof w Beadzie i zamknij `.101`.
4. Claimuj dokładnie `.102.1`; nie claimuj kontenera `.102` równocześnie.

Program wykonawczy jest opublikowany w Beads. High-level gates:
S1 identity → S2 source binding/research → S3 content kinds → S4 idempotent
production command → S5 reviews → S6 target mapping → S7 ActionObject/readback
→ S8 trzy vertical proofs → S9 wszystkie 57 keep → S10 global QA → S11 runtime
projection/robot gate → S12 final audit/merge/runtime.

Atomowe dzieci i kolejność:
- .102.1 exact source-pack binding
- .102.2 source-to-decision registry refresh
- .102.3 immutable per-URL research packet
- .103 landing/hub authorization path (service/editorial już mają własne typy)
- .104 idempotent production command i no-regeneration guard
- .105.1 deterministic anti-slop/privacy gate
- .105.2 typed independent review runs + finding dispositions
- .105.3 REACH work-item/semantic recovery
- .106.1 page the_content discovery + typed failures
- .106.2 full-clone ACF mapping + confirmation receipt
- .106.3 seven legacy readback mapping reconciliations
- .107.1 persisted expected/observed digests
- .107.2 global content_dev_draft_create authoritative readback
- .108.1 editorial the_content vertical proof
- .108.2 service ACF approved-revision reuse proof
- .108.3 landing/hub vertical proof
- .109.1 current-approved keep cohort
- .109.4 code-fixable source/service/work-item repairs
- .109.2 page-bound GSC source-ready cohort
- .109.3 source-ready cohort without page metrics
- .109.5 true external blocker audit
- .110.1 canonical/intent/duplicate/FAQ graph
- .110.2 internal links/orphans/anchors/CTA destinations
- .110.3 title/meta/snippet/structured-data gates
- .110.4 accessibility + non-keep policy audit
- .111.1 runtime projection + canonical CSV materializer
- .111.2 non-bypassable robot_ready gate
- .112.1 full completion audit + independent reviews
- .112.2 all merges + clean managed runtime handoff

Dependencies są zapisane w Beads i bd dep cycles ma być pusty. Nie claimuj
high-level group oraz child jednocześnie; group jest kontenerem, child jest
implementation WIP. Po zamknięciu wszystkich dzieci zamknij parent z proofem.

WILQ API jest mózgiem produktu. Przed decyzją strategiczną fetchuj aktualny
/api/content/diagnostics i odpowiednie typed API reads. Page-bound GSC może
ustalać priorytet tylko z evidence ID, dimensions i freshness. Brak metryki nie
jest zerem. GA4/Ahrefs domain/batch context nie jest page-level tie-breakerem.
Nigdy nie zmyślaj metryk, źródeł, prawa, rezultatów SEO ani credential statusu.

Aktualny baseline do ponownej walidacji:
- 214 URL-i: 57 keep / 87 noindex / 46 redirect / 24 remove;
- 18 current approved revisions;
- 17 semantic zero-findings + 1 REACH unavailable;
- 8 legacy dev readback observations, ale tylko 1 confirmed_the_content;
  pozostałe 7 nie spełnia exact mapped completion;
- 38/57 keep ma page-bound GSC, 16 ma catalog entry bez metrics, 3 bez matchu;
- robot_ready = 0.

Priorytetowe URL-e z ostatniego page-bound GSC evidence
ev_refresh_refresh_google_search_console_0e332cb3bb35 (jednodniowy,
partial_possible snapshot; odśwież przed użyciem): BDO, operat wodnoprawny,
Europejski Zielony Ład, remediacja, outsourcing środowiskowy, doradztwo i
outsourcing, szkolenia, pozwolenie zintegrowane, homepage, OOS. BDO i operatu
nie pisz ponownie; wykorzystaj istniejące rewizje. Europejski Zielony Ład miał
dev REST blocker. Pierwsza nowa treść po zielonym pipeline: remediacja albo
outsourcing, zależnie od świeżego WILQ readiness. Pierwsze szybkie reuse:
doradztwo/outsourcing, szkolenia i homepage po exact mappingu.

Research i jakość:
- używaj high-trust primary sources: Google Search Central/QRG, oficjalne
  urzędy/akty dla prawa oraz adekwatne papers; practitioner guidance tylko z
  jawnym ograniczeniem autorytetu;
- źródło ma URL, checked_at, scope, freshness i adopt/reject/lab-test;
- packet per URL: exact intent/query cluster, canonical owner, audience/problem,
  approved facts, blocked claims, regulatory needs, CTA i internal links;
- deterministic gates przed judge: schema, lineage, legal/privacy, język,
  long_sentence, heading_answer_mismatch/exaggeration, vague answer,
  thin_section, wall_of_text, working_note, duplicate paragraph, weak CTA;
- corpus-wide duplicate/intent/link preflight przed revision i rerun po kohorcie;
- osobne read-only reviews: content/UX, SEO/intent/cannibalization/meta,
  factual/regulatory/source fidelity, potem WILQ semantic review;
- critical accepted finding tworzy exact child revision; dobrego approved
  dokumentu nie generuj ponownie.

Opencode second opinion:
- używaj wyłącznie skillowego runnera opencode-second-opinion;
- exact model: opencode-go/deepseek-flash (DeepSeek V4.1 Flash), nigdy
  deepseek-v4-flash;
- run dir w .krn/runs/opencode-second-opinion/<run-id>/;
- poll wyłącznie check-opinion.sh; completed tylko przy checker exit 0 i
  opinion/meta/raw;
- każde finding musi dostać lokalną dyspozycję; advisory nie jest approvalem;
- usuń run po zakończeniu jego konsumenta.

WordPress/dev authority:
- wyłącznie create-only dev draft przez exact ActionObject lifecycle:
  validate → preview → review → confirm → execute → audit → authoritative GET;
- wymagaj revision ID/digest i kompletnego mapping receipt;
- ACF: pełny component→writable-leaf clone, zero częściowego fallbacku;
- the_content/page: exact direct REST observation;
- public publish, production update/delete, masowa mutacja i vendor bypass są
  poza authority. Nie czytaj ani nie wypisuj .env; raportuj tylko sanitized
  credential presence/source/status.

Każdy update użytkownika podaje: owner, evidence, changed paths, unknowns i next
action. Nie mów „gotowe”, dopóki requirement-by-requirement audit nie dowodzi:
214-row validator przeciw authoritative SQLite; 57/57 exact mapped dev draft
readback albo true external typed blocker; zero critical findings; global QA;
pełne CI; wszystkie PR-y merged; Beads zamknięte; repo/worktrees uporządkowane;
managed API http://127.0.0.1:8000 i dashboard
http://127.0.0.1:5173/command-center ready na merged main. Dopiero wtedy oznacz
goal complete. W każdym innym stanie kontynuuj następny bezpieczny Bead.
```

## Stan publikacji

Prompt jest retained handoffem. Graf Beads został opublikowany lokalnie;
zależności nie mają cykli. Bieżący S1 pozostaje `in_progress` do finalnego
review/PR/CI/merge. Ten dokument sam nie jest proofem wykonania programu.
