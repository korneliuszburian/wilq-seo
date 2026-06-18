# Source Registry

Last checked: 2026-06-17.

| Source | Domain | Why it matters | Product decision | Location |
| --- | --- | --- | --- | --- |
| OpenAI Codex goal docs | Codex | Durable objective workflow | Goal execution and stop condition | `docs/goals/001-goal.md` |
| OpenAI Codex Skills | Codex | Repo skills use SKILL.md, references and scripts | Late skill creation with `$skill-creator` | `docs/architecture/codex-runtime.md` |
| OpenAI Codex Hooks | Codex | Lifecycle scripts for SessionStart/Stop | `.codex/hooks.json` | `docs/architecture/codex-runtime.md` |
| OpenAI Codex MCP | Codex | MCP as tool/context adapter | `docs/architecture/mcp-policy.md` | `docs/architecture/mcp-policy.md` |
| OpenAI Codex Subagents | Codex | Parallel read-heavy workflows | `AGENTS.md` subagent workflow | `AGENTS.md` |
| OpenAI Codex noninteractive | Codex | `codex exec` smoke tests and schema outputs | future Codex smoke gate | `docs/architecture/codex-runtime.md` |
| OpenAI Codex approvals and security | Codex security | Sandbox/approval modes and network access behavior | `codex_skill_eval.sh` uses network-enabled workspace-write for local API proof | `docs/research/codex-noninteractive-skill-evals-research.md` |
| OpenAI Codex noninteractive skill eval research | Codex evals | `codex exec`, schemas, JSONL traces and local API sandboxing | WILQ skill eval harness | `docs/research/codex-noninteractive-skill-evals-research.md` |
| Matt Pocock skills | Agent skills | Small composable skills and reusable agent workflows | WILQ skills stay focused and smoke-tested | `docs/research/codex-noninteractive-skill-evals-research.md` |
| AGENTS.md | Agent instructions | Persistent repo guidance | root `AGENTS.md` | `AGENTS.md` |
| Google Ads API mutate best practices | Google Ads | Real write layer and validation | ActionObject write model | `docs/architecture/action-model.md` |
| Google Ads Recommendations API | Google Ads | Recommendation review capability | Ads capability pack | `docs/architecture/google-ads-capability-pack.md` |
| Google Ads Quality Score | Google Ads | Quality diagnostics | Ads expert rules | `wilq/expert/ads/quality_score.yaml` |
| Google Ads negative keywords | Google Ads | Waste reduction actions | Ads expert rules | `wilq/expert/ads/negative_keywords.yaml` |
| Google Ads responsive search ads | Google Ads | RSA validation | Ads expert rules | `wilq/expert/ads/responsive_search_ads.yaml` |
| Official Google Ads MCP server | Google Ads MCP | Read-only MCP bridge to Google Ads API; Python/stdio; OAuth or service-account auth | Future Ads Doctor adapter inspiration, not product brain | `docs/architecture/mcp-policy.md`, `.agents/skills/wilq-ads-doctor/references/output-contract.md` |
| BDOS.ai | Product inspiration | AI operating-system pattern for Google Ads specialists and PPC teams | Ads Doctor and WILQ command-center product inspiration; WILQ remains API/evidence-first | `docs/architecture/system-overview.md` |
| BDOS-class WILQ operating-system bar | Product architecture | Capability matrix across Ads, Merchant, GA4, GSC, Ahrefs, Localo, WordPress and social | Reject connector-dashboard slop; require evidence, tactics, safety and ActionObjects before UI polish | `docs/architecture/bdos-class-wilq-operating-system.md` |
| WILQ marketing source map | Product research | Source-to-skill compiler contract for Ads, GSC, GA4, Merchant, Ahrefs, Localo, copywriting and social | Every serious marketing slice must condense sources into knowledge/rules/API view models/skills/evals | `docs/research/wilq-marketing-source-map.md` |
| Google Search Console Search Analytics | SEO | Query/page CTR and position data | GSC opportunities | `wilq/expert/seo/gsc_opportunities.yaml` |
| Ahrefs API v3 | SEO | Gap and competitor data | Ahrefs connector boundary | `docs/architecture/connector-registry.md` |
| Localo API/MCP integration | Local SEO | Local visibility connector | Localo connector boundary | `docs/architecture/connector-registry.md` |
| WordPress REST API | CMS | Read/write content inventory | WordPress connectors | `docs/architecture/connector-registry.md` |
| LinkedIn Posts API | Social | Organization publishing | Social Publisher | `wilq/expert/social/linkedin_rules.yaml` |
| Facebook Pages API | Social | Page publishing | Social Publisher | `wilq/expert/social/facebook_rules.yaml` |
| RAG | Retrieval | External memory improves factuality | knowledge cards before prompts | `docs/research/retrieval-and-knowledge-patterns.md` |
| Lost in the Middle | Retrieval | Long context can hide facts | compact context packs | `docs/research/retrieval-and-knowledge-patterns.md` |
| Self-RAG | Retrieval | Retrieval and critique loops | future evals | `docs/research/retrieval-and-knowledge-patterns.md` |
| RAGAS | Evaluation | Retrieval quality metrics | future evals | `docs/research/retrieval-and-knowledge-patterns.md` |
| ReAct | Agent/tool use | Reasoning plus acting against external tools | WILQ skills must call API before claims | `docs/research/codex-noninteractive-skill-evals-research.md` |
| Toolformer | Tool use | Tool selection and API call discipline | allowed endpoint lists in skills | `docs/research/codex-noninteractive-skill-evals-research.md` |
| Reflexion | Agent feedback | Verbal feedback loops for iterative improvement | eval findings feed skills/references | `docs/research/codex-noninteractive-skill-evals-research.md` |
| CRITIC | Agent critique | Tool-interactive self-correction | deterministic checks before self-critique | `docs/research/codex-noninteractive-skill-evals-research.md` |
| DSPy | Prompt programs | Programmatic prompt/eval modules | skills as measurable modules | `docs/research/codex-noninteractive-skill-evals-research.md` |
| G-Eval | LLM-as-judge | Judge layer caveats and bias | judge only after deterministic gates | `docs/research/codex-noninteractive-skill-evals-research.md` |
| The Prompt Report | Prompting survey | Structured prompting and delimiter patterns | XML-like eval prompts plus schema outputs | `docs/research/codex-noninteractive-skill-evals-research.md` |
| WILQ marketing playbooks | Knowledge | Source-grounded operator playbooks | compiled knowledge cards before Codex context | `wilq/knowledge/playbooks/marketing_playbooks.yaml` |
| Ruff | Quality | Python lint | `scripts/lint.sh` | `docs/architecture/quality-gates.md` |
| mypy | Quality | Python types | `scripts/typecheck.sh` | `docs/architecture/quality-gates.md` |
| pre-commit | Quality | local checks | `.pre-commit-config.yaml` | `docs/architecture/quality-gates.md` |
| Bandit | Security | Python security lint | `scripts/security.sh` | `docs/security/agentic-threat-model.md` |
| pip-audit | Security | dependency audit | `scripts/security.sh` | `docs/security/agentic-threat-model.md` |
| Semgrep | Security | static security patterns | `scripts/security.sh` | `docs/security/agentic-threat-model.md` |
| ESLint | Frontend | JS/TS lint | dashboard lint | `apps/dashboard/eslint.config.js` |
| TypeScript | Frontend | static checks | dashboard typecheck | `apps/dashboard/tsconfig.json` |
| Vitest | Frontend | route tests | dashboard tests | `apps/dashboard/src/routes/App.test.tsx` |
| Playwright | Frontend | future e2e smoke | planned gate | `docs/architecture/quality-gates.md` |
| Zod | Frontend | runtime validation at API boundaries | shared API response schemas | `packages/shared-schemas` |
| TanStack Query | Frontend | API server-state cache | dashboard API calls | `apps/dashboard/src/lib/api.ts` |
| Demand Gen migration | Google Ads | Display migration readiness | Demand Gen architecture | `docs/architecture/demand-gen-migration.md` |
| Custom audiences and Keyword Planner | Google Ads | Segment workflow | custom-segments architecture | `docs/architecture/custom-segments-from-search-terms.md` |
| GA4 Data API | Analytics | behavior diagnostics | GA4 architecture | `docs/architecture/ga4-diagnostics.md` |
| Merchant API | Merchant | product/feed diagnostics | Merchant architecture | `docs/architecture/merchant-center-and-feed.md` |
| Google Sheets API | Collaboration | export/import surface | Sheets architecture | `docs/architecture/google-sheets-operator-surface.md` |
| OWASP LLM | Security | prompt injection and agent risk | threat model | `docs/security/agentic-threat-model.md` |
| NIST AI RMF | Risk | AI risk management | model runtime policy | `docs/architecture/model-runtime-policy.md` |
