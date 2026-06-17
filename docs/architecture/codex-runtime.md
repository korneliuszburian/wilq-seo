# Codex Runtime

Codex Desktop/CLI is the primary operator runtime. Codex operates WILQ API; it does not invent metrics.

Official OpenAI Codex manual anchors checked on 2026-06-17:

- Skills: `https://developers.openai.com/codex/skills`
- AGENTS.md: `https://developers.openai.com/codex/guides/agents-md`
- MCP: `https://developers.openai.com/codex/mcp`
- Hooks: `https://developers.openai.com/codex/hooks`
- Subagents: `https://developers.openai.com/codex/subagents`
- Non-interactive mode: `https://developers.openai.com/codex/noninteractive`

Repo runtime surfaces:

- `AGENTS.md` contains durable repo rules.
- `.codex/hooks.json` declares SessionStart and Stop hooks.
- `.codex/hooks/` contains hook scripts that avoid secret printing.
- `.agents/skills/` contains Goal 001 repo-scoped WILQ skills created with `$skill-creator`.
- `wilq-daily-command` is wired to WILQ API through `POST /api/codex/context-pack` and `scripts/smoke_context_pack.py`.
- Other WILQ skills are production-shaped stubs with `SKILL.md`, `references/output-contract.md`, `scripts/smoke_skill_contract.py`, allowed endpoint lists, evidence requirements, output contracts and safety rules.

Skill timing rule:

```txt
Policy first, skill folders after API contracts.
Create or expand WILQ skills only when their WILQ API endpoints and smoke-test paths exist.
```

Goal 001 skill folders:

```txt
wilq-daily-command
wilq-ads-doctor
wilq-gsc-content-doctor
wilq-ahrefs-gap-finder
wilq-localo-operator
wilq-content-strategist
wilq-social-publisher
wilq-campaign-builder
wilq-custom-segments
wilq-demand-gen-operator
wilq-ga4-analyst
wilq-merchant-feed-operator
```

Skill verification:

```bash
python3 .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
python3 .agents/skills/wilq-merchant-feed-operator/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
scripts/verify.sh
```

Non-interactive Codex skill evals:

```bash
scripts/codex_skill_eval.sh --all --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 scripts/codex_skill_eval.sh --skill wilq-demand-gen-operator --api-base http://127.0.0.1:8000
```

Notes:

- Eval outputs are local proof artifacts under `.local-lab/evals/codex-skill/` and are intentionally git-ignored.
- The harness uses `codex exec --json --output-schema` and validates final JSON against `docs/evals/schemas/wilq-skill-eval-result.schema.json`.
- Local WILQ API evals need network-enabled sandboxing. The harness defaults to `workspace-write` plus `sandbox_workspace_write.network_access=true` and tells Codex not to edit files.
- Use `CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1` when global user MCP/plugin config causes unrelated transport failures.
- 2026-06-17 proof: 12/12 Goal 001 skills produced non-interactive eval results with `api_used=true`, `language=pl-PL`, Polish diacritics and schema validation pass. Many results are intentionally blocked because smoke scripts expose readiness/counts but not enough concrete evidence IDs for marketing recommendations.
