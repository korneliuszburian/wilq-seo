# Content Pipeline Quality Gap — research report

Rola dokumentu: `current state / retained reviewer evidence` dla Beada
`wilq-seo-1oa.36.36`. Fixed point implementacji A–C: `1686215b`. Raport nie
zastępuje `docs/architecture/system-map.md`, WILQ API ani Beads. Został
zaktualizowany po live readbacku 2026-08-09; task state pozostaje w Beads.

## 1. Finding A (CRITICAL): semantic review instruction is fragmented

**Disposition: RESOLVED.** Slice A został zaakceptowany i zintegrowany do
`main` (`25a10ed0`, merge `1918c6e2`). Poniższy opis zachowuje przyczynę i
uzasadnienie falsifiera; nie opisuje już bieżącego defektu.

`wilq/content/quality/semantic_review_turn.py:17-47` builds `_INSTRUCTION` as one
concatenated Python string. Several sentences are broken fragments stitched
together, e.g.:

- `"Nie zatwierdzaj tekstu, nie przepisuj go, nie wymyślaj faktów ani targetów, nie twórz "` — ends mid-sentence; next fragment starts `"W wymiarze repetition wykrywaj także..."`
- `"...Każdy finding ma być instrukcją dla człowieka i "` — ends with dangling `i `; next fragment starts `"Dla regulowanego profilu sprawdź osobno..."`
- `"wskazywać exact target z dozwolonej listy. W affected_targets używaj wyłącznie ..."` — appears after the regulatory paragraph with no grammatical anchor.

This is not a cosmetic issue: the model receives an incoherent Polish instruction,
so per-dimension findings, the `affected_targets` rule, the `evidence_ids` rule and
the one-finding-per-dimension rule can be dropped or misread. It is the strongest
candidate explanation for weak/`needs_changes` review outcomes recorded in the
active REVIEW-ULTRA bead `wilq-seo-813a.48` and in past review packets.

Supporting facts (verified at HEAD):

- `CONTENT_SEMANTIC_DIMENSIONS` (9 dims) in
  `wilq/content/quality/semantic_review_contracts.py` is well-typed and versioned.
- `semantic_review_output_schema` (`semantic_review_turn.py:119-136`) correctly
  restricts enums to real dimensions, targets and evidence IDs, so the *schema*
  is sound; only the *instruction* is broken.
- Deterministic gates (`wilq/content/quality/review.py`) already enforce safety
  (forbidden claims, evidence lineage, duplicate risk) but they are negative
  gates, not quality gates.

## 2. Finding B: draft prompt has no marketer-grade copy directive

**Disposition: RESOLVED.** Slice B został zaakceptowany jako
`content_initial_draft@v2` (`4bb2cea4`, merge `0b48515a`). Dyrektywy używają
istniejących pól planu i nie rozszerzają uprawnień ani źródeł faktów.

Poprzedni `content_initial_draft@v1` instruował strukturę, JSON, CTA-safety i
regulatory assertions, ale nie mówił modelowi:

- how to use `angle` and `value_proposition` (both exist in `compact_semantic_review_proposal` / planning proposal and are passed into the draft turn),
- how to use `target_reader`, `buyer_problem`, `buyer_trigger`, `baseline_cta_direction`,
- to write a strong, specific CTA (deterministic gate `_weak_cta` only rejects 3 literal phrases: `kliknij tutaj`, `skontaktuj się`, `czytaj dalej` — `review.py:820-823`),
- to avoid filler/water language, to make each section answer its `reader_question` directly,
- any reading-quality/emotion/flow guidance ("feeling czytania" in the goal).

The result: the model knows *what* to keep and *what* to avoid legally, but not
*how to write well*. That is the gap between "contract-correct draft" and
"marketer-grade draft".

## 3. Finding C: real BDO loop requires one human decision

**Disposition: NEEDS REVIEW.** Live WILQ API nie zawiera stron
`/oferta/bdo/` ani `/bdo/` w aktualnym WordPress inventory. Kanonicznym,
kompletnym work itemem BDO jest obecnie:

`content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`

dla `https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/`.

Istniejąca rewizja nr 37 jest immutable i ma human review `approved`, lecz
WILQ oznacza ją jako pochodzącą z wcześniejszego planu. Aktualny operator
journey zatrzymuje się na `scope_review_required`; review i dev draft są
zablokowane przez `revision_context_changed`. Rewizja ma 7
`source_material_ids`, 4 karty wiedzy i reviewed regulatory lineage, więc
historyczne twierdzenie o pustych materiałach nie jest już prawdziwe.

Slice D wykonał świeży plan i immutable draft tylko dla tego exact work itema.
Plan `content_planning_proposal_7a16b3006dbe477e883d2d94b6c6c985`
zawiera 13 evidence IDs, 7 source materials i 4 knowledge cards. Pierwsza próba
draftu (`codex_content_initial_draft_bacf8a1863da4d5cb10e3b9de83816d6`)
pozostała fail-closed po trzech falach assurance i nie zapisała rewizji. Ten
realny run ujawnił ograniczenie orkiestracji do jednej rundy deterministycznej.

Po focused fixie bounded fixed-point druga próba
`codex_content_initial_draft_b130b99623284728bd17302b61c867e0` utworzyła
immutable rewizję nr 38
`content_revision_862e57ac267546038e763280dc29cacc`, digest
`a7b974c3da66dba952931ae8d7d756fc063f69cdc41ddd682a2159b3488c21ba`.
Rewizja ma 8 sekcji, 3 FAQ i 2 CTA; regulatory assurance przeszło, a
`publish_ready=false` pozostało bez zmian.

Exact semantic review
`content_semantic_review_614d94b8d9604140a1e9aa78c5d5eded` zmierzyło
9 wymiarów: 8 `strong`, 1 `needs_changes`. Jedyny finding ma severity `medium`
i dotyczy `repetition`: deterministyczny guard wykrył frazę „Źródło wskazuje”
w sekcji 08 o karach. Review jest związane z 13 evidence IDs i connectorami
`google_search_console`, `wordpress_ekologus`, `public_site` oraz
`official_regulatory_review`.

Owner-facing odczyt kanonicznego preview pokazuje, że finding automatyczny jest
węższy niż faktyczny zakres redakcyjny. Nie jest to decyzja człowieka, lecz
pakiet wejściowy do niej. Rekomendowana decyzja: `needs_changes`, ponieważ:

- sekcja 02 powtarza prawie ten sam zakres podmiotów i kończy się wewnętrzną
  notatką o weryfikacji przez człowieka;
- sekcje 03 i 04 krzyżują zakresy: fragment o papierowej ewidencji znajduje
  się pod nagłówkiem o zwolnieniach, a fragment o zwolnieniach pod nagłówkiem
  o papierowej ewidencji;
- sekcja 05 powtarza regułę KPO i ponownie wprowadza poboczny fragment o
  dokumentach papierowych;
- sekcje 06–08 zawierają język roboczy typu „według dostarczonej instrukcji”,
  „informacje pochodzą z publikacji” albo „wymagają weryfikacji”, zamiast
  gotowego, naturalnego tekstu dla przedsiębiorcy;
- sekcja 07 powtarza opis logowania i ról użytkowników, a sekcja 08 powtarza
  opis sankcji; daty, terminy i kwoty nadal wymagają świadomego sprawdzenia
  przez Wilku przed jakąkolwiek akceptacją.

Minimalna notatka do decyzji `needs_changes`: „Usuń meta-komentarze i
duplikaty, przywróć zgodność sekcji 03–04 z nagłówkami oraz pozostaw daty,
terminy i sankcje wyłącznie po exact weryfikacji źródłowej.”

Read-only editorial integrity dla rewizji 38: 8/8 reprezentacji `aligned`,
0 `mismatch`; wynik `structural_change_observed` względem starej rewizji 37,
ponieważ świeży plan zmienił identyfikatory i układ sekcji. Lint wykazał:
`em_dash=1`, `repeated_root_nale=7`, `repeated_sentence_opening=4`. Próba exact
`repair-proposal` dla sekcji 08 została prawidłowo zablokowana kodem
`revision_not_ready_for_proposal`: brakuje decyzji człowieka dla rewizji 38.
Nie powstała child revision, ActionObject ani vendor write.

## 4. Gap model

```text
contracts + deterministic safety gates (present, sound)
        x
draft instruction (structure+JSON+safety only)
        x
semantic review instruction (BROKEN)
        =>
candidate drafts are structurally valid but unpredictable in reading quality
```

Stan warstw:

1. L1 — **DONE**: spójna semantic review instruction, bez zmiany kontraktu.
2. L2 — **DONE**: `content_initial_draft@v2` z marketer-grade directives.
3. L3 — **DONE**: typed `thin_section`, `wall_of_text` i rozszerzony weak CTA.
4. L4 — **NEEDS REVIEW**: measured packet istnieje; exact child repair czeka na
   decyzję Wilku dla rewizji 38.

## 5. Slices (ordered, one WIP at a time)

- Slice A (L1) — **DONE**: repair `_INSTRUCTION` in `semantic_review_turn.py`. Proof:
  focused test asserting the instruction contains complete sentences / the key
  rules as whole phrases (e.g. not ending mid-sentence; contains
  `affected_targets`, `evidence_ids`, one-finding-per-dimension, `publish_ready=false`).
  Behavior-preserving apart from the prompt text; no contract change.
- Slice B (L2) — **DONE**: add marketer-grade directive to the draft prompt. Proof: prompt
  render test + existing draft tests still green.
- Slice C (L3) — **DONE**: extend deterministic gates. Proof: focused falsifiers for each new
  finding code (weak CTA with value-less text; filler-laden section; section not
  answering its reader_question).
- Slice D (L4) — **NEEDS REVIEW**: live BDO run + measured review packet są
  zapisane powyżej. Jeśli Wilku po przeczytaniu rewizji 38 wybierze
  `needs_changes`, należy zapisać exact human review dla jej digestu, ponowić
  `repair-proposal` wyłącznie dla sekcji 08 i uruchomić nowe semantic review na
  child revision. Nie wolno zapisać tej decyzji w imieniu Wilku.

## 6. Stop conditions

- No change weakens exact revision, evidence lineage, redaction or ActionObject
  safety (AGENTS.md).
- No vendor write / publish / update / delete; `publish_ready=false` remains.
- No invented facts, targets, metrics; every verdict ties to revision + evidence IDs.
- "10/10" or "marketer-grade" is claimed only after real Wilku UAT, never from a
  synthetic run.
