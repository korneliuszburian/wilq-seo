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
- `.agents/skills/` is intentionally empty until the API context-pack and validation contracts are ready.
- Future skills must be created with `$skill-creator`, then reviewed for scope creep.

Skill timing rule:

```txt
Policy first, skill folders later.
Create WILQ skills only after their WILQ API endpoints and smoke-test paths exist.
```

