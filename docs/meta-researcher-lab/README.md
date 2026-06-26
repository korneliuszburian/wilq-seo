# Meta-Researcher Lab

Auto-optimization loop for WILQ skill prompts. Inspired by karpathy/autoresearch (automated experiment loops) but applied to prompt engineering instead of model training.

## Problem Statement

"Upodledzone" (smaller/commodity) LLM models generate lower-quality code from skills. Better prompts partially compensate, but there's no **systematic method** to discover which prompts work best. Manual iteration is slow and subjective.

## Solution: Endless Experimentation Loop

```
Task Generator → Skill Execution → Quality Eval → Prompt Improvement → Repeat
```

Each cycle:
1. **Generates** a frontend task (component, layout, style fix)
2. **Runs** a skill (or a standalone prompt) against it
3. **Evaluates** output against a quality contract
4. **Improves** the prompt based on evaluation results
5. **Logs** results for cross-skill comparison

## Architecture

```
.wilq-meta-researcher/
  SKILL.md                              # The meta-researcher skill
  agents/openai.yaml                    # Interface metadata
  references/
    output-contract.md                  # Quality contract for research output
    eval-metrics.md                     # Eval metric definitions
    prompt-patterns.md                  # Best-practice prompt patterns
  scripts/
    task_generator.py                   # Generate frontend tasks + ideal output
    eval_runner.py                      # Run promptfoo + custom evals
    prompt_optimizer.py                 # Analyze failures → propose prompt changes
    benchmark_suite.sh                  # Orchestrate full loop
  benchmark/
    cases/                              # Benchmark task definitions
    results/                            # Eval results per iteration
    prompts/                            # Versioned prompt snapshots
```

## Core Patterns

### Pattern 1: /goal for Endless Loop

```
/goal Zbadaj wszystkie skillsy, uruchom benchmark, wygeneruj raport z wynikami

# Evaluator (Haiku) sprawdza po każdej turie:
# - Czy benchmark się skończył?
# - Czy wszystkie skillsy zostały przetestowane?
# - Czy raport jest kompletny?
```

**Limitation:** Evaluator only judges what's surfaced in conversation. It does NOT run commands or read files independently. Your goal condition must be written so Claude's output demonstrates it.

**Workaround:** Use Bash hooks (`PostToolUse`) to write eval results to a file, then have the evaluator check the file content in conversation.

### Pattern 2: /loop for Recurring Research

```
/loop 30m /research-run

# gdzie .claude/loop.md contains:
# 1. Read latest benchmark results
# 2. Identify lowest-scoring prompt
# 3. Propose improvement
# 4. Run eval on improved prompt
# 5. Update skill if improvement verified
```

**Limitation:** Tasks only fire when Claude Code is idle. Max 50 scheduled tasks. 7-day expiry.

### Pattern 3: Agent Spawning for Parallel Eval

```python
# Spawn 3 parallel agents:
# 1. Explore: find all frontend-related skills
# 2. General-purpose: run benchmark on 4-6 skills
# 3. Explore: collect eval results
```

### Pattern 4: Promptfoo Integration

```yaml
# promptfooconfig.yaml
models:
  - id: local-qwen36-35b-a3b
    label: "our-model"
    config:
      api_base: http://127.0.0.1:18182
      api_key: ${ANTHROPIC_API_KEY}

prompts:
  - file: benchmark/cases/001-login-component.md

default_test:
  environment:
    - API_BASE: http://127.0.0.1:18182

tests:
  - vars:
      task: "Stwórz komponent logina z walidacją"
      style_guide: "tailwind-v3"
    assert:
      - type: contains
        value: "className"
      - type: javascript
        value: "result.includes('required') || result.includes('pattern')"
      - type: llm-rubric
        value: "Kod powinien używać Tailwind CSS, zawierać walidację HTML5, i być w formie pojedynczego komponentu React"
```

### Pattern 5: Smoke Script as Quality Gate

Every skill already has a `smoke_skill_contract.py`. Use it as a **hard gate** in the benchmark:

```bash
# benchmark_suite.sh
for skill in .agents/skills/wilq-*/; do
  skill_name=$(basename "$skill")
  
  # Run smoke test
  python "$skill/scripts/smoke_skill_contract.py" --base-url "$API_BASE" || {
    echo "FAIL: $skill_name smoke test"
    continue
  }
  
  # Run eval
  promptfoo eval --config promptfooconfigs/"$skill_name".yaml
done
```

## FAQ

### Q: /goal evaluator nie widzi wyników benchmarku, bo nie czyta plików

**A:** Three approaches:
1. **Surface results in conversation** — Claude runs the eval, reads the output, and pastes it into the chat. The evaluator can then judge it.
2. **Use a Bash hook** — `PostToolUse` hook writes results to a file, Claude reads the file, and the evaluator checks the conversation.
3. **Use /loop instead of /goal** — /loop fires when Claude is idle, so it doesn't depend on the evaluator. It's less "goal-directed" but more reliable for batch work.

**Recommendation:** Use `/loop 30m` for the research loop. /goal is too fragile for batch evals.

### Q: Promptfoo nie obsługuje local models

**A:** Promptfoo supports any OpenAI-compatible API. Your setup uses `ANTHROPIC_BASE_URL=http://127.0.0.1:18182`, so configure promptfoo:

```yaml
models:
  - id: local-qwen36-35b-a3b
    config:
      provider: openai
      apiBase: http://127.0.0.1:18182
      model: local-qwen36-35b-a3b
```

### Q: Jak mierzyć "jakość kodu" automatycznie?

**A:** Multi-layer approach:

| Layer | Metric | Tool |
|-------|--------|------|
| **Syntax** | Compiles without errors | `python -m py_compile` / `npx next lint` |
| **Structure** | Has required components/sections | Grep for keywords |
| **Contract** | Passes smoke test | `smoke_skill_contract.py` |
| **LLM rubric** | Human-like quality assessment | `llm-rubric` assert in promptfoo |
| **Diff against ideal** | Semantic similarity to ideal output | Custom script |

### Q: Czy to nie będzie generować śmieci?

**A:** Tylko z **słabymi metrykami**. Kluczowe guardrails:

1. **Smoke test jako hard gate** — jeśli skill nie przechodzi smoke'a, prompt nie jest oceniany
2. **llm-rubric z konkretnym kryterium** — nie "czy jest dobry", ale "czy używa X, Y, Z"
3. **Cross-skill comparison** — porównujesz ten sam prompt na różnych skillsach, nie absolutne score'y
4. **Human-in-the-loop** — najgorsze i najlepsze prompty są flagowane do ręcznej recenzji

### Q: Context7 do czego służy w tym kontekście?

**A:** Context7 to MCP server, który dostarcza **aktualną dokumentację** do promptu Claude'a. W kontekście meta-researcher:

- **Globalna konfiguracja:** `claude mcp add --scope user context7 -- npx -y @upstash/context7-mcp --api-key YOUR_KEY`
- **Zasada:** Dodaj do globalnego `.claude/settings.json` regułę, że przy niepewności model musi potwierdzać standardy przez Context7 (oficjalna docs) lub internet.
- **W skillsach:** Skillsy mogą używać Context7 do fetchowania latest API docs, co poprawia jakość outputu.

### Q: Jak versionować prompty?

**A:** Directory structure:

```
benchmark/prompts/
  ads-doctor/
    v1-original.md
    v2-after-eval-20260626.md
    v3-after-loop-20260626.md
  content-strategist/
    v1-original.md
    ...
```

Każdy prompt ma frontmatter:
```yaml
---
version: v2
date: 2026-06-26
eval_score: 4.2/5
changes_from: v1
changes: "Usunąłem dwuznaczne instrukcje o kolorach, dodałem przykład layoutu"
---
```

### Q: /goal vs /loop — kiedy użyć którego?

| | /goal | /loop |
|---|---|---|
| **Cel** | "Zrób X i zwróć kontrolę gdy gotowe" | "Powtarzaj Y co Z minut" |
| **Evaluator** | Sprawdza warunek po każdej turze | Brak — po prostu uruchamia prompt |
| **Tryb** | Single-session, directional | Recurring, session-scoped |
| **Do benchmarku** | ✅ Single run (wszystko naraz) | ✅ Recurring research (ciągła optymalizacja) |
| **Fragilność** | Wysoka (evaluator nie czyta plików) | Niska (fires when idle) |

### Q: Jakie zadania frontendowe do benchmarku?

**Tier 1 — Simple (syntax + structure):**
- Form component with validation
- Card/grid layout
- Navigation bar
- Modal/dialog
- Toast/notification

**Tier 2 — Medium (logic + state):**
- Search with debounce
- Tabbed interface
- Accordion/folder tree
- Data table with sorting
- File upload with preview

**Tier 3 — Complex (integration + patterns):**
- Dashboard with charts
- Drag-and-drop list
- Real-time chat UI
- Multi-step wizard
- Responsive data grid

Każde zadanie ma:
- `task.md` — brief zadania
- `ideal.md` — "idealny" output (reference)
- `constraints.md` — style guide, tech stack, forbidden patterns

## Integration with Existing Infrastructure

### smoke_skill_contract.py

Already exists per skill. Use as **hard gate** — if smoke fails, skip eval for that skill run.

### eval_marketing_brief.sh

Runs language + structure checks on `/api/marketing/brief`. Can be extended to check skill output language compliance.

### skill_hygiene_check.py

Validates that skill prose doesn't contain "workaround", "bugfix", "outdated", etc. Use as **pre-benchmark hygiene gate**.

### codex_skill_eval.sh

Runs Codex against each skill. This is already a benchmark. The meta-researcher lab should **extend** this, not replace it — codex_eval measures raw skill output, meta_researcher measures prompt improvement over time.

## Context7 Global Rule

Add to `~/.claude/settings.json` (global):

```json
{
  "env": {
    "CONTEXT7_ENABLED": "1"
  },
  "hooks": {
    "PostToolUse": [
      {
        "match": {
          "tool": "Write",
          "specifier": "**/SKILL.md"
        },
        "type": "prompt",
        "prompt": "Check this SKILL.md change against official documentation. Are there any API endpoints, connector names, or contract references that might be outdated? Confirm with Context7 or web search if uncertain."
      }
    ]
  }
}
```

Or simpler: add to the global `CLAUDE.md`:

```markdown
## Rule: Verify Against Official Sources
When uncertain about any standard, API contract, or best practice, always confirm with official sources:
1. Context7 MCP for library docs
2. Web search for latest changes
3. Official documentation links in references/
Never guess — if evidence is missing, return a blocker.
```

## Next Steps

1. [ ] Install Context7 globally
2. [ ] Create `.wilq-meta-researcher/` skill structure
3. [ ] Define benchmark task suite (Tier 1-3 frontend tasks)
4. [ ] Configure promptfoo for local model
5. [ ] Write `task_generator.py`
6. [ ] Write `eval_runner.py`
7. [ ] Write `prompt_optimizer.py`
8. [ ] Wire up `benchmark_suite.sh`
9. [ ] Test single iteration
10. [ ] Set up /loop for recurring research
