# Long-running delivery loop — plan, pi mechanics, standards

Status: decision + reference record (2026-09-27). Supersedes ad-hoc "continue"
prompting described in earlier handoffs; does not supersede `PLANS.md`,
`docs/CONTEXT.md`, Beads, or the active capsule.

## 1. What "long-running" has to solve here

WILQ delivery runs one writer, WIP=1, slice-by-slice, with durable external state
(Beads + `.krn` capsule) and strict verification per slice. The failure modes we
must design against:

1. Context exhaustion mid-slice (loses the plan and the verification trail).
2. Unbounded loops (agent keeps "continuing" without progress).
3. Silent scope creep (a "continue" that starts an unauthorized publish/merge).
4. Stale handoff state (markdown plans that compete with Beads).
5. Budget blindness (no stop condition, so the last slice is left half-built).

## 2. Pi mechanics that matter (v0.87.1, verified in local docs)

| Mechanism | Fact | Use for WILQ |
| --- | --- | --- |
| Compaction summary format | Built-in structured summary has `## Goal`, `## Progress` (Done / In Progress / Blocked), `## Key Decisions`, `## Next Steps`, `## Critical Context` (`docs/compaction.md`) | The capsule + Bead comments already carry this shape; compaction therefore preserves the plan if the plan is written durably each slice |
| Compaction knobs | `compaction.enabled`, `reserveTokens` (16384), `keepRecentTokens` (20000), per-model `modelOverrides` (`docs/settings.md`) | For a 1M-context model, override so compaction triggers late (e.g. reserve/keep scaled up) instead of at the default threshold |
| Manual compaction | `/compact [instructions]` | Before a long slice, compact with instructions pointing at the capsule + active Bead |
| Bounded continuation | `turn_end` and `agent_before_settle` handlers may return `continue: true` for **one** next model request; "guard continuation conditions because an unconditional continuation can loop" (`docs/extensions.md`) | Safe primitive for an auto-continue extension, but only with an explicit iteration/budget guard |
| Run end | After `agent_end`, retries, recovery, compaction, or queued work can continue (`docs/extensions.md`) | An extension can re-trigger one more turn, or an external driver can re-invoke |
| External driver | `pi --continue` continues the most recent project session; `-p/--print` runs one-shot and exits (`docs/cli.md`) | `while` loop over `pi --continue --print "<next step>"` gives long-running autonomy without the owner typing each time |
| Exact session control | `--session-id <id>`, `PI_SESSION_ID`, `PI_SESSION_FILE` | Bind the driver to one named session so it never resumes an unrelated thread |
| Context introspection | `PI_PROVIDER`, `PI_MODEL`, `PI_REASONING_LEVEL`; `/session` shows statistics | Budget checks and provenance in logs |
| Skills vs extensions | Skills are on-demand instructions; extensions are executable integration points | Keep the WILQ procedure as a skill/plan doc; use an extension only if we need in-process auto-continue |

Conclusion: the cheapest reliable "does not need the owner to keep typing" is an
**external driver loop** over `pi --continue --print`, plus a **bounded
auto-continue** only if we later want in-process continuation. Both must stop on
explicit markers and a hard iteration cap.

## 3. The driver (implemented)

`scripts/long_running_loop.sh`:

- Requires explicit opt-in (`WILQ_LOOP=1`) so it cannot be started accidentally.
- Takes one step-prompt file and an optional session id.
- Runs `pi --continue --print` (or `--session-id`) once per iteration, always
  from the repository root, logging stdout+stderr to
  `.krn/runs/long-running/<stamp>/iter-NN.txt`.
- Stops on the first of: stop marker in the output (`LOOP: DONE`,
  `LOOP: BLOCKED`, `LOOP: BUDGET`), a non-zero exit, or `WILQ_LOOP_MAX_ITERS`
  (default 3).
- Refuses to run when the working tree is dirty in the tracker files or when
  `WILQ_LOOP_REQUIRE_CLEAN=1` and `git status --porcelain` is non-empty (so the
  loop never stacks uncommitted slices).

Per-iteration contract for the agent (encoded in the step prompt): one Bead,
claim -> focused falsifier RED->GREEN -> gates -> owner review of local proof
(and, if useful, a fresh read-only Codex advisory pass) -> one commit -> push ->
close Bead -> capsule update -> print exactly one stop marker. The previous
DeepSeek step is historical, not an executable instruction.

## 4. Standards the loop enforces

1. **One durable state owner per fact.** Beads own task state; the capsule owns
   the restart fixed point; docs own decisions. No parallel markdown TODO list.
2. **Bounded work unit.** Exactly one slice per iteration, one observable
   result, one cohesive commit. No iteration starts a second Bead.
3. **Verification before claim.** Focused falsifier RED->GREEN (mutation proof
   for test-only slices), typed gates for the changed boundary, pre-existing
   reds recorded and never masked.
4. **Review per slice** by the delivery owner: inspect the fixed diff, rerun
   focused proof and disposition each finding in `.krn` and the Bead. Only Codex
   models may be invoked; for an additional advisory pass use a fresh, read-only
   Codex context over one bounded artifact. A Codex-family pass after a Codex
   implementation is not an independent-family review or approval. Historical
   DeepSeek results remain records, not gates for the current Codex-only goal.
5. **Fixed point before stop.** Every stop (marker, error, budget) leaves HEAD
   pushed, tree green, next step in the Bead and capsule.
6. **Authority boundaries.** No vendor write, no product deploy/publication, no
   credential operations, WordPress draft-only; PR/merge/publish stay owner
   decisions. The loop must print `LOOP: BLOCKED` rather than acting outside
   authority.
7. **Freshness honesty.** Missing/stale evidence produces typed blockers; the
   loop never invents metrics or "ready" claims.
8. **Budget accounting.** The step prompt requires a context check at the start;
   above the working limit the agent prints `LOOP: BUDGET` and stops instead of
   starting a new slice.

## 5. Backlog plan (bd ready order, WIP=1)

| Order | Bead | Slice plan |
| --- | --- | --- |
| 1 | `wilq-seo-blyi` S1 — DONE (f8b36e802) | Fixture first: add `tests/content/delivery_identity_fixtures.py` building a schema-valid reconciled `ContentDeliveryIdentityBinding` + classification lookup (mirror `store_delivery_identity._classification_lookup_for_binding`). Then re-apply `wilq/content/workflow/delivery_identity_recovery.py` (status `current`/`drift`/`classification_missing`, exact current row identity, typed `safe_next_step`), the store lookup method, and `GET /api/content/delivery-identities/{binding_id}/drift-recovery`; falsifier drift/current/missing + mutation proof |
| 2 | `wilq-seo-blyi` S2 — S2a receipt (8b8bb0854), S2b store (f4daac638) and producer (77208fdd5) DONE; ActionObject wiring open | Supersede/re-mint through the existing ActionObject lifecycle: record the supersession, mint the rebound identity from the current row, append-only + idempotent, no vendor write |
| 3 | `wilq-seo-blyi` S3 (open) | Projection guard so a drifted identity can never render as usable anywhere (records, projections, operator surfaces) |
| 4 | `wilq-seo-82dx` | Exact BDO authority chain for the latest classification: delivery identity -> source-fact review/promotion -> source-pack binding, no foreign/global fallback; stop at typed blockers where evidence is missing |
| 5 | `wilq-seo-0mpo` | Durable typed review receipt for public Service Profile cards (append-only, idempotent, conflict, stale-on-drift), flips only the API-owned lifecycle projection to `approved_current` |
| 6 | `wilq-seo-s7po` | Testable current-page and official-primary researcher adapter (deterministic fake + typed blockers, no live vendor write) |
| 7 | rest of `bd ready` | Continue in listed order; skip owner-decision items |
| parked | `wilq-seo-87hv`, `wilq-seo-eyt0` | Owner decisions (official-source registration policy; homepage Service Profile card policy) — the loop prints `LOOP: BLOCKED` if only these remain |

Non-ready follow-ups already recorded: `wilq-seo-dv0x` (inject
`ApplyDependencies.content_snapshot_loader`, typing), snapshot-loader-absent
branch in initial-draft status, `kkig` dev-preview upstream authority, `2ray`
stale-cache refetch, `p0cl` hardcoded panel sentence, `mwta` tile render test,
`ke4p` first-blocker only.

## 6. Operating the loop

```bash
# one bounded run per invocation is still available:
WILQ_LOOP=1 WILQ_LOOP_MAX_ITERS=3 \
  scripts/long_running_loop.sh .krn/loop/step.md
```

Stop markers: `LOOP: DONE` (queue exhausted), `LOOP: BLOCKED` (owner decision or
external blocker), `LOOP: BUDGET` (context/budget limit reached).

## 6b. Loop history

- 2026-09-27: plan + driver published (9873b10ef); blyi S1/S2a/S2b-store/S2b-producer pushed; branch fast-forward merged into `main` and pushed (`origin/main == origin/wip`); protected PNG relocated to `.krn/runs/proofs/`; sqlite schema inventory red fixed (65bd29cea).

## 7. Open owner decisions

1. PR for `wip/dirty-integration-20260916` (push + upstream already done).
2. `bd dolt remote add origin <url>` then `bd dolt push` (currently no remote).
3. Retention of `act_content_material_review_e74a3e493bdf2` (PNG, deliberately
   untracked).
4. Whether to enable an in-process auto-continue extension in addition to the
   external driver.
