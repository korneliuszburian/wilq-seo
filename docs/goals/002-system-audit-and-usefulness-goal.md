# Goal 002 - System Audit, Anti-Slop Contracts and Plug-And-Play Proof

Last updated: 2026-06-18.

This is the next audit goal after Goal 001 cleanup. Keep this file short and
operational. Do not turn it into a work log.

## Purpose

Audit WILQ from A to Z so the product follows engineering discipline and gives
real leverage to a Polish marketer.

This goal exists because WILQ must not become:

- a connector dashboard,
- stale readiness text,
- prompt-only advice,
- over-engineered scaffolding,
- duplicate contracts that disagree,
- slow UI that hides useful work behind loading states.

## Engineering Rules To Enforce

Use these rules as audit criteria:

1. Think before coding:
   - state assumptions,
   - name ambiguity,
   - ask when the target is unclear,
   - surface tradeoffs.

2. Simplicity first:
   - minimum code that solves the proven problem,
   - no speculative abstractions,
   - no unused configurability,
   - delete complexity introduced by our own changes.

3. Surgical changes:
   - touch only files needed for the goal,
   - keep local style,
   - remove only dead code caused by our changes,
   - mention unrelated dead code instead of deleting it.

4. Goal-driven execution:
   - every task has success criteria,
   - every fix has focused verification,
   - broad claims require broad evidence.

## Audit Scope

Audit these surfaces for stale state, duplicate contracts, fake usefulness and
performance waste:

- WILQ API endpoint contracts.
- Command Center view model.
- Dashboard route copy and loading behavior.
- Connector readiness vs live vendor data.
- ActionObject queue and validation state.
- Opportunities and tactical queue.
- Knowledge cards and expert rules.
- Marketing source condensation from `docs/research/wilq-marketing-source-map.md`.
- Codex context packs.
- WILQ skill instructions and smoke scripts.
- Non-interactive Codex eval prompts and outputs.
- MCP policy and whether a WILQ MCP server is justified.

## Command Center Audit Questions

For every visible Command Center section ask:

1. What decision does this give a marketer?
2. What evidence IDs support it?
3. What action can the marketer safely take?
4. What claims are blocked?
5. Is this live evidence, readiness, fixture, stale state or generic copy?
6. Is the same truth shown in Codex context packs and WILQ skills?
7. Is this section worth keeping on the first screen?

If a section cannot answer those questions, it should be rewritten, moved lower,
collapsed, or removed.

## Source-To-Product Audit Questions

For every Ads, SEO, Merchant, GA4, Localo, Ahrefs, WordPress or social claim ask:

1. Which source in `docs/research/wilq-marketing-source-map.md` or a newer
   verified source justifies this rule?
2. Where is the condensed rule stored: knowledge card, expert YAML, schema,
   connector adapter, API view model or skill reference?
3. Which WILQ evidence fields are required before the claim is allowed?
4. Which Polish prompt template or skill output uses the rule?
5. Which non-interactive Codex eval proves the rule works against WILQ API?

If the answer is "only in a prompt" or "only in a dashboard string", the rule is
not implemented yet.

## Performance Audit

Command Center must feel usable. Audit:

- backend latency of `/api/dashboard/command-center`,
- extra endpoint latency after the first screen,
- frontend loading time,
- duplicate fetches,
- expensive computed view-model code,
- unnecessary first-screen data,
- heavy evidence/action lists that can be truncated or lazy-loaded.

Preferred fixes:

1. Make first-screen API response fast.
2. Lazy-load secondary panels.
3. Truncate evidence lists and expose detail links.
4. Cache expensive local view-model joins.
5. Avoid broad refactors until profiling proves the bottleneck.

## Plug-And-Play Market Advantage Test

Run a clean session comparing:

- plain Codex with no WILQ context,
- Codex with WILQ skills and WILQ API,
- dashboard/API output.

Use Polish prompts:

- `Pokaż 3 najważniejsze decyzje marketingowe na dziś dla Ekologus.`
- `Co w Ads mogę uczciwie powiedzieć na podstawie obecnego evidence?`
- `Którą treść odświeżyć albo stworzyć i czego nie wolno obiecywać?`
- `Czy Merchant ma problem z produktami/feedem i jaki ActionObject sprawdzić?`
- `Czy Localo daje już ranking/GBP insight czy nadal blocker?`

Pass criteria:

- Polish output with Polish diacritics.
- WILQ API was used.
- Evidence IDs and source connectors appear.
- No invented metrics.
- Same facts as dashboard for the same claim.
- Clear next safe action.
- Blocked claims are explicit.

## Done Criteria

Goal 002 is done only when:

- stale/outdated Command Center states are removed,
- slow first-screen causes are measured and addressed,
- every visible first-screen section has a marketer decision purpose,
- WILQ skills prove useful Polish API-backed outputs,
- MCP decision is evidence-based,
- all changes pass focused checks and full `scripts/verify.sh`.
