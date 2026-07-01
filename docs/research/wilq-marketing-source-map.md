# WILQ Marketing Source Map

Last checked: 2026-06-18.

This file is the source-to-product map for WILQ skills, expert rules, knowledge
cards and dashboard view models. It is not a blogroll. A source is useful only
when it becomes a typed WILQ contract, Polish operator prompt pattern, evidence
requirement, blocked-claim rule or safe ActionObject path.

## Compiler Rule

For every source-backed feature, produce this chain:

```txt
source -> extracted principle -> required WILQ evidence -> blocked claims
-> knowledge card or expert rule -> API view model -> dashboard/skill output
-> non-interactive Codex eval
```

Do not ship prompt text as the only implementation. If a source changes a
marketing decision, encode it in YAML/schema/API behavior first, then expose it
through dashboard and skills.

## Agent And RAG Method Sources

| Source | URL | WILQ use |
| --- | --- | --- |
| ReAct | https://arxiv.org/abs/2210.03629 | Skill pattern: think about the task, call WILQ API, answer from observed evidence. |
| Self-RAG | https://arxiv.org/abs/2310.11511 | Evidence sufficiency gate: retrieve, critique, then answer or block. |
| RAGAS | https://arxiv.org/abs/2309.15217 | Eval dimensions: context relevance, faithfulness, answer relevance. |
| RAG evaluation survey | https://arxiv.org/abs/2405.07437 | Broader RAG test vocabulary for retrieval and generation quality. |
| OpenAI Codex manual | https://developers.openai.com/codex/ | Skills, AGENTS.md, MCP, non-interactive mode, hooks and subagents. |
| Matt Pocock skills | https://github.com/mattpocock/skills | Small composable skills with references/scripts instead of prompt dumps. |

Required WILQ output:

- every WILQ skill lists allowed endpoints and evidence requirements,
- every skill response contains source connectors and evidence IDs,
- every skill has deterministic smoke plus `codex exec` eval,
- every Polish prompt template asks for facts, diagnosis, next action, blocked
  claims and evidence.

## Google Ads Sources

| Source | URL | WILQ use |
| --- | --- | --- |
| Google Ads API docs root | https://developers.google.com/google-ads/api/docs/ | Primary entry point for current Google Ads API docs; feature work must still link the exact subpage that defines the contract. |
| Google Ads API Recommendations | https://developers.google.com/google-ads/api/docs/recommendations | Fetch recommendation types and optimization score, then filter through WILQ rules before action. |
| Google Ads API Custom Audiences | https://developers.google.com/google-ads/api/docs/remarketing/audience-segments/custom-audiences | Build review-only custom segment payload previews from evidence-backed terms; never apply targeting without validation, forecast/audience context and audit. |
| Google Ads negative keywords | https://support.google.com/google-ads/answer/2453972 | Search-term waste workflow and negative keyword candidate safety checks. |
| Google Ads Query Language | https://developers.google.com/google-ads/api/docs/query/overview | GAQL contracts; no arbitrary model-written GAQL in apply paths. |
| Google Ads Query Builder | https://developers.google.com/google-ads/api/fields/ | Interactive field/resource discovery pattern for explicit query contracts. |
| Google Ads Query Validator | https://developers.google.com/google-ads/api/docs/query/validator | GAQL syntax and compatibility validation pattern before live reads. |
| Google Ads API Explorer | https://developers.google.com/google-ads/api/docs/developer-toolkit/api-explorer | Live HTTP/JSON prototyping pattern; WILQ persists only sanitized evidence and blocker labels. |
| Google Ads MCP server | https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server | Read-only account discovery, GAQL search and resource metadata adapter pattern; MCP output is not a recommendation until WILQ stores evidence. |
| Google Ads API Developer Assistant | https://developers.google.com/google-ads/api/docs/developer-toolkit/what-is-developer-assistant | Mission-control pattern for Ads engineering: intent-level request, schema/version inspection, validation, read-only execution and diagnostics. |
| Google Ads partial failures | https://developers.google.com/google-ads/api/docs/best-practices/partial-failures | Bulk preview/apply must expose per-operation failures. |
| Google Ads REST mutate | https://developers.google.com/google-ads/api/rest/common/mutate | ActionObjects must model typed operations, validation and audit. |
| Performance Max asset groups | https://developers.google.com/google-ads/api/performance-max/asset-groups | PMax creative/assets diagnostics and campaign builder constraints. |
| PMax asset best practices | https://support.google.com/google-ads/answer/14528220 | Asset completeness and format checks before creative recommendations. |
| SEA content generation research | https://thearf-org-unified-admin.s3.amazonaws.com/MSI_Report_23-136.pdf | Human-in-the-loop ad copy generation with attribute-enriched prompts and cost/performance context. |

WILQ must produce:

- Ads Doctor read packs for campaigns, search terms, recommendations, quality,
  change history, budgets, impression share and PMax asset readiness.
- Polish prompt templates for:
  - waste review,
  - negative keyword candidate review,
  - campaign quality review,
  - PMax asset gap review,
  - client answer about performance drop.
- Blocked claims: wasted spend, CPA, ROAS, conversion drop, search-term waste or
  budget pacing unless the matching Ads/GA4 evidence exists.

## SEO, GSC, Ahrefs And WordPress Sources

| Source | URL | WILQ use |
| --- | --- | --- |
| Google SEO Starter Guide | https://developers.google.com/search/docs/fundamentals/seo-starter-guide | Content quality, crawl/index understanding and practical page improvements. |
| Google Search Central docs | https://developers.google.com/search/docs | Technical SEO and Search feature constraints. |
| Google Search Console API overview | https://developers.google.com/webmaster-tools | REST access to Search Console properties, sitemaps, Search Analytics and URL testing; WILQ should expose only permission-backed, evidence-tagged reads. |
| Google Search Console Search Analytics API | https://developers.google.com/webmaster-tools/v1/searchanalytics/query | Query/page evidence contract for clicks, impressions, CTR and position. |
| Search Analytics query guide | https://developers.google.com/webmaster-tools/v1/how-tos/search_analytics | GSC read contracts must check available dates first, account for typical 2-3 day data delay, paginate with `rowLimit`/`startRow`, and label detailed page/query/country/device reads as potentially partial. |
| Search Analytics performance data guide | https://developers.google.com/webmaster-tools/v1/how-tos/all-your-data | Daily one-day reads, 25k-row paging and aggregation-by-page/site caveats inform WILQ freshness and completeness blockers. |
| Ahrefs content gap analysis | https://ahrefs.com/blog/content-gap-analysis/ | Gap workflow: competitor terms only after inventory/cannibalization check. |
| Ahrefs keyword research | https://ahrefs.com/seo/keyword-research | Traffic potential and intent grouping as context, not unsupported forecasts. |
| SEO strategy evolution research | https://www.tandfonline.com/doi/full/10.1080/23311975.2025.2491678 | Content quality, technical SEO and user experience as integrated SEO criteria. |

WILQ must produce:

- query/page matrix with CTR, position, impressions, clicks and freshness,
- WordPress inventory match before create/refresh/merge decisions,
- content brief prompts in Polish:
  - `odśwież istniejącą treść`,
  - `stwórz nową treść tylko jeśli brak inventory match`,
  - `połącz lub zablokuj duplikat`,
  - `wyjaśnij klientowi bez obietnic rankingu`.
- Blocked claims: ranking guarantee, lead uplift, revenue impact and traffic
  forecast without supporting evidence.

## GA4 Sources

| Source | URL | WILQ use |
| --- | --- | --- |
| GA4 Traffic acquisition report | https://support.google.com/analytics/answer/12923437 | Source/medium and campaign quality diagnosis. |
| GA4 ecommerce measurement | https://developers.google.com/analytics/devguides/collection/ga4/ecommerce | Product/revenue/event contracts when ecommerce evidence exists. |
| GA4 Data API | https://developers.google.com/analytics/devguides/reporting/data/v1 | Typed report requests and dimensions/metrics. |

WILQ must produce:

- landing/source/campaign quality review,
- tracking gap diagnosis for `(not set)`, zero engagement, missing landing or
  missing conversion context,
- conversion/revenue claims only when GA4 key event or ecommerce evidence exists.

## Merchant Center And Feed Sources

| Source | URL | WILQ use |
| --- | --- | --- |
| Merchant Center product data specification | https://support.google.com/merchants/answer/7052112 | Feed attributes, product eligibility and disapproval prevention. |
| Merchant listing structured data | https://developers.google.com/search/docs/appearance/structured-data/merchant-listing | Product structured data checks for merchant visibility. |
| Merchant API | https://developers.google.com/merchant/api | Product/feed diagnostics and issue read contracts. |

WILQ must produce:

- product/feed issue review queue,
- product attribute completeness checks,
- supplemental-feed-first candidate logic where possible,
- blocked claims: approval recovery, revenue recovery or automatic feed edit
  without validated ActionObject and audit.

## Localo And Local SEO Sources

| Source | URL | WILQ use |
| --- | --- | --- |
| Localo MCP/API Integration docs | Localo in-app help article | OAuth/MCP readiness, token type and current adapter limitation. |
| Google Business Profile local ranking factors | https://support.google.com/business/answer/7091 | Relevance, distance and prominence framing; no paid/local rank guarantee. |
| Business Profile Performance API | https://developers.google.com/my-business/reference/performance/rest | GBP performance reports and search keyword impressions where access exists. |
| GBP performance insights help | https://support.google.com/business/answer/9918094 | Profile views, clicks and customer interaction framing. |

WILQ must produce:

- exact Localo blocker if OAuth access token is missing,
- local ranking/GBP performance only after Localo or GBP evidence exists,
- local SEO prompts for visibility drop, review blockers, GBP task queue and
  competitor comparison, all in Polish.

## Copywriting, Content And Social Sources

| Source | URL | WILQ use |
| --- | --- | --- |
| LLMs for customized marketing content generation and evaluation | https://www.amazon.science/publications/llms-for-customized-marketing-content-generation-and-evaluation-at-scale | Critic model/human oversight pattern for draft quality. |
| LLM-generated ads persuasion research | https://arxiv.org/html/2512.03373v1 | Persuasion principles need controlled evaluation, not blind generation. |
| Generative AI and marketing review | https://scholars.unh.edu/cgi/viewcontent.cgi?article=3393&context=faculty_pubs | GenAI marketing impact areas and governance caveats. |

WILQ must produce:

- Polish prompt templates for ad copy, landing copy, article refresh, social
  post and client-response drafts,
- every draft must include source facts it is allowed to mention,
- every draft must include claims it must avoid,
- no social publish action unless permissions and ActionObject validation exist.

## Source-To-Skill Prompt Contract

Every mature WILQ skill prompt should follow this Polish shape:

```txt
Zadanie operatora: <co marketer chce osiągnąć>
Źródła WILQ: <endpointy/API context>
Wymagane evidence: <metryki, evidence IDs, freshness>
Reguły eksperckie: <knowledge cards / YAML rules>
Zablokowane claimy: <czego nie wolno mówić>
Bezpieczne akcje: <ActionObjects / prepare-only / blocker>
Odpowiedź: po polsku, krótko, z decyzją i następnym krokiem
```

The eval must fail if the output:

- lacks Polish diacritics,
- invents a metric,
- omits evidence IDs/source connectors,
- recommends a write without ActionObject validation,
- shows readiness-only text as a marketing decision,
- cannot be matched back to dashboard/API state.
