# OpenAI-Aligned WILQ Skill Evals

This is the explicit evaluation contract for WILQ Codex skills. The goal is not
to prove that a prompt can produce valid JSON. The goal is to prove that a real
Polish marketer command produces a useful WILQ decision: current evidence,
blocked claims, safe next step and workflow-specific interpretation.

## OpenAI Baseline

This layer follows the OpenAI eval pattern:

- Define the task before prompt tuning.
- Run production-like test inputs, not toy examples.
- Use structured criteria/graders, not vibes.
- Inspect failures, tag them and iterate on the system.
- Treat eval data and harnesses as product assets.

OpenAI docs map to WILQ this way:

- `data_source_config`: `docs/evals/cases/wilq-skill-eval-cases.json`
- `testing_criteria`: `docs/evals/schemas/wilq-skill-eval-result.schema.json`
  plus `scripts/codex_skill_eval.sh` deterministic checks.
- model sample output: the final JSON from `codex exec`.
- per-item inputs: realistic Polish marketer prompts in each eval case.
- graders: schema validation, connector/evidence/action checks, blocked-claim
  checks, Polish-language checks, freshness handling and operator usefulness.
- analysis loop: `docs/evals/skill-eval-ledger.md` plus Beads follow-up tasks.

## Required Quality Bar

Every WILQ skill eval must answer five questions:

1. Czy operator dostał decyzję, a nie dump pól z API?
2. Czy decyzja ma dowody: `source_connectors`, `evidence_ids` and action IDs
   where relevant?
3. Czy skill blokuje claims without proof: ROAS, revenue, conversion impact,
   legal/current-law/product effects and measurement-window claims?
4. Czy freshness jest obsłużona aktywnie: refresh, repair path albo jawny
   blocker, zamiast biernego snapshotu?
5. Czy next step is safe and concrete enough that Wilku can use it without a
   developer translating raw API state?

The default non-interactive gate requires `operator_usefulness_score >= 4`.
Score `3` is a guardrail pass only and must be treated as a product gap, not as
BDOS-class quality.

## Eval Case Requirements

Each case should include:

- `skill`
- realistic `task_pl` or `messy_task_pl`
- expected/required source connectors
- route or workflow markers in `expected_terms_pl`
- expected, forbidden or blocked action IDs when the workflow exposes actions
- blocked claim terms for unsupported marketing conclusions
- forbidden connectors/terms for common overreach

Run the static coverage audit before broad non-interactive evals:

```bash
rtk uv run python scripts/audit_skill_eval_coverage.py --strict
```

Then run the skill eval:

```bash
rtk scripts/codex_skill_eval.sh --skill <skill> --api-base http://127.0.0.1:8000
```

## Failure Policy

If a skill returns a technically valid but weak answer, do not patch around it
only in the prompt. First decide where the missing product truth belongs:

- API/schema/view-model when the system lacks a typed decision, priority,
  blocker, proof summary, freshness state or safe next action.
- connector/action service when evidence, refresh or validation is missing.
- skill contract only when the API already exposes the right fields but the
  operator workflow is not using them well.

The fix is complete only after deterministic smoke and non-interactive evals
prove the improved behavior.
