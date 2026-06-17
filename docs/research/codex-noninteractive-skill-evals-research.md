# Codex non-interactive, skille i evale WILQ

Data researchu: 2026-06-17  
Zakres: Codex `exec`, repo-skille, subagenci, evale jakości, polskie odpowiedzi operatora, inspiracje Google Ads MCP i BDOS.ai.

## Konkluzja

WILQ powinien testować skille jak product workflows, nie jak pliki Markdown. Minimalny standard to cztery bramki dla każdego skillu:

1. **Statyczna bramka skillu**: poprawny `SKILL.md`, `references/`, `scripts/`, allowed endpoints, no-invented-metrics guardrail, polski output contract.
2. **Deterministyczna bramka API**: skrypt smoke odpala WILQ API, pobiera context-pack/status/evidence/action state i blokuje skill, gdy brakuje źródeł.
3. **Non-interactive bramka Codex**: `codex exec --json --output-schema ...` uruchamia skill na standardowym zadaniu i zapisuje maszynowo ocenialny wynik.
4. **Użyteczność dla polskiego marketera**: odpowiedź jest po polsku, z polskimi znakami, zawiera dowody, ryzyko, gotowy następny krok i nie wymaga zgadywania, co operator ma zrobić.

Najważniejsza decyzja architektoniczna: MCP serwery i skille nie mogą stać się mózgiem systemu. Mózgiem zostaje WILQ API: connector status, evidence IDs, opportunities, ActionObjects, validation i audit. MCP jest adapterem. Skille są operatorskimi workflowami nad API. `codex exec` jest harnesssem do powtarzalnego dowodzenia jakości.

## Co wynika z oficjalnych dokumentów Codex/OpenAI

### `codex exec`

Oficjalny tryb non-interactive Codex jest przeznaczony do CI, pre-merge checks, scheduled jobs i workflowów CLI. Kluczowe właściwości dla WILQ:

- `codex exec "prompt"` uruchamia agenta bez TUI.
- Domyślnie działa w read-only sandbox; automatyzacja powinna nadawać najniższe wymagane uprawnienia.
- `--json` wypisuje JSONL z eventami, w tym start/stop tur, wiadomości agenta, tool calls, command executions i usage.
- `--output-last-message <path>` zapisuje finalną odpowiedź.
- `--output-schema <schema.json>` wymusza finalną odpowiedź zgodną z JSON Schema.
- Piped stdin może być dodatkowym kontekstem albo całym promptem.
- W automatyzacji z API key token nie powinien być job-level env, jeżeli w tym samym jobie uruchamia się repo-controlled code.

Źródło: https://developers.openai.com/codex/noninteractive

Sandbox/approval nuance: read-only non-interactive runs are appropriate for file-only checks, but local API evals need a network-capable sandbox. Official approvals/security docs describe `read-only`, `workspace-write` and network access as distinct controls, so WILQ evals use `workspace-write` with `sandbox_workspace_write.network_access=true` for localhost API proof.

Źródło: https://developers.openai.com/codex/agent-approvals-security

Praktyczny wzorzec dla WILQ:

```bash
codex exec \
  --json \
  --sandbox workspace-write \
  -c 'approval_policy="never"' \
  -c sandbox_workspace_write.network_access=true \
  --output-schema docs/evals/schemas/wilq-skill-eval-result.schema.json \
  --output-last-message ".local-lab/evals/wilq-ads-doctor.json" \
  -C /home/krn/coding/krn/active/wilq-seo \
  'Użyj $wilq-ads-doctor. Odpowiedz po polsku. Oceń gotowość Google Ads i wskaż tylko rekomendacje z evidence IDs.'
```

To daje dwa artefakty:

- JSONL trace z pełną trajektorią agenta.
- Finalny JSON zgodny ze schema, łatwy do walidacji w CI.

Uwaga praktyczna z lokalnego smoke testu: `read-only` jest właściwy do suchych odczytów repo, ale nie wystarcza do WILQ API evali, bo sandbox może blokować network access, także do `127.0.0.1`. Eval, który ma realnie wywołać lokalne WILQ API, powinien używać `workspace-write` z `sandbox_workspace_write.network_access=true` albo `danger-full-access` tylko w zewnętrznie izolowanym runnerze. Prompt i walidator nadal muszą zakazywać edycji plików.

### Repo-skille

Codex skanuje repo-skille z `.agents/skills` od aktualnego katalogu do repo root. Skill to katalog z wymaganym `SKILL.md` oraz opcjonalnymi `scripts/`, `references/`, `assets/`, `agents/`. Skille działają przez progressive disclosure: Codex widzi nazwę/opis, a pełny `SKILL.md` czyta dopiero po aktywacji.

Źródło: https://developers.openai.com/codex/skills

Wniosek dla WILQ:

- `description` musi być krótki, konkretny i trigger-friendly, bo Codex może skracać listę skillów.
- `SKILL.md` ma zawierać workflow, allowed endpoints, safety i wymagany output.
- Długa wiedza Ads/SEO/content powinna być w `references/`.
- Deterministyczne checki powinny być w `scripts/`.
- Każdy skill musi mieć smoke prompt i smoke script, bo samo istnienie katalogu nie dowodzi runtime usefulness.

### Subagenci

Codex subagenci pomagają wtedy, gdy praca jest równoległa i read-heavy: eksploracja, testy, logi, audyty, porównania źródeł. Nie startują automatycznie; trzeba ich jawnie poprosić. Subagenci dziedziczą sandbox/approval. Najlepszy wzorzec to wąski agent z jasną rolą i małym tool surface.

Źródło: https://developers.openai.com/codex/subagents

Wniosek dla WILQ:

- Subagenci nie powinni sami pisać ActionObjects ani wykonywać zmian.
- Dobre role: Evidence Auditor, Ads Rules Reviewer, Polish UX Reviewer, Safety/Audit Reviewer, Connector Readiness Reviewer.
- Parent agent konsoliduje wyniki i dopiero wtedy tworzy plan lub rekomendacje.
- `agents.max_depth = 1` jest wystarczające; głębszy fan-out zwiększa koszt i chaos.

### Prompting i structured outputs

OpenAI prompt engineering guide podkreśla, że promptowanie to iteracyjna, testowana praktyka, a bardziej złożone aplikacje muszą walidować zachowanie na realnych przykładach. Structured Outputs są właściwe, gdy downstream potrzebuje stabilnych pól, ale schema sama nie gwarantuje prawdziwości danych; prompt musi opisać, co zrobić przy niepasującym lub brakującym wejściu.

Źródła:

- https://developers.openai.com/api/docs/guides/prompt-engineering
- https://developers.openai.com/api/docs/guides/structured-outputs
- https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide

Wniosek dla WILQ:

- `--output-schema` jest dobry do evali, nie do „magicznego” wymuszania prawdy.
- Schema musi zawierać pola typu `evidence_ids`, `source_connectors`, `blocked_reason`, `polish_language_ok`, `action_validation_state`.
- Prompt ewaluacyjny powinien mówić: jeśli API/evidence nie wystarcza, zwróć blocker, nie rekomendację.

## Synteza paperów

### ReAct: reason + act, ale z API jako źródłem prawdy

ReAct pokazuje wartość przeplatania rozumowania i działań narzędziowych. W QA/fact verification redukuje hallucination przez interakcję z zewnętrznym źródłem. WILQ powinien używać tego wzorca tak:

- agent rozumuje o zadaniu,
- pobiera context-pack/status/evidence z WILQ API,
- dopiero na podstawie wyników formułuje diagnozę,
- jeżeli brakuje danych, wraca z blockerem.

Źródło: https://arxiv.org/abs/2210.03629

### Toolformer: agent ma wiedzieć, kiedy narzędzie jest potrzebne

Toolformer formalizuje decyzję: kiedy wywołać API, z jakimi argumentami i jak użyć wyniku. Dla WILQ to argument za allowed endpoint lists w skillach. Skill nie może mieć dowolnego narzędziowego chaosu; powinien mieć jawnie dozwolone endpointy i warunki użycia.

Źródło: https://arxiv.org/abs/2302.04761

### Reflexion: feedback loop bez trenowania modelu

Reflexion pokazuje, że agent może poprawiać decyzje przez językowy feedback i pamięć epizodyczną. Dla WILQ oznacza to, że eval harness powinien zapisywać:

- co skill próbował zrobić,
- gdzie zabrakło dowodu,
- co poprawić w skillu/API,
- czy następny run rozwiązał ten sam błąd.

To ma być feedback do skill references i expert rules, nie luźna notatka w rozmowie.

Źródło: https://arxiv.org/abs/2303.11366

### Self-RAG: retrieval on demand + self-critique

Self-RAG pokazuje, że retrieval powinien być adaptacyjny, a model powinien krytykować własną generację względem retrieved evidence. Dla WILQ:

- context-pack nie powinien ładować „wszystkiego”,
- skill powinien pobierać tylko właściwe źródła,
- finalna odpowiedź musi odróżniać fakt, interpretację i brak danych,
- output powinien mieć sekcję `Walidacja` albo `Blokery`.

Źródło: https://arxiv.org/abs/2310.11511

### Lost in the Middle: mniej prompt stuffing, więcej skondensowanych kart

Badanie long-context pokazuje, że modele gorzej korzystają z informacji umieszczonej w środku długiego kontekstu. To jest mocny argument przeciw wrzucaniu całego „podręcznika marketera” do jednego prompta.

Źródło: https://arxiv.org/abs/2307.03172

WILQ powinien:

- kompilować wiedzę do krótkich knowledge cards,
- trzymać lineage/confidence/freshness,
- ładować tylko karty pasujące do skillu,
- trzymać najważniejsze constraints na początku i końcu promptu/eval promptu.

### RAGAS i ARES: ewaluuj retrieval, faithfulness i relevance osobno

RAGAS proponuje reference-free metryki dla RAG: czy kontekst jest trafny, czy odpowiedź jest wierna kontekstowi i czy sama odpowiedź jest jakościowa. ARES rozdziela context relevance, answer faithfulness i answer relevance oraz używa syntetycznych danych i małej liczby ludzkich adnotacji.

Źródła:

- https://arxiv.org/abs/2309.15217
- https://arxiv.org/abs/2311.09476

WILQ mapping:

- `context_relevance`: czy skill pobrał właściwe connector/evidence.
- `answer_faithfulness`: czy każda rekomendacja ma evidence IDs i nie dodaje metryk spoza API.
- `answer_relevance`: czy odpowiedź daje marketerowi realny następny krok.
- `safety`: czy brak write/apply bez validated ActionObject.

### G-Eval i LLM-as-judge: używać ostrożnie

G-Eval pokazuje, że LLM-judge może być przydatny przy ocenie jakości tekstu, ale paper wskazuje też bias w kierunku LLM-generated text. WILQ nie może opierać prawdy o kampaniach na judge. Judge jest tylko warstwą po deterministycznych checkach.

Źródło: https://arxiv.org/abs/2303.16634

Bezpieczny układ:

1. deterministic schema/API checks,
2. regex/JSON checks na evidence IDs, connector IDs, Polish diacritics,
3. dopiero potem LLM judge dla clarity/usefulness.

### CRITIC: external feedback > samoocena bez narzędzi

CRITIC pokazuje wzorzec self-correction z użyciem zewnętrznych narzędzi. Dla WILQ self-critique ma używać API, testów, schema validatora i skill smoke scripts, a nie tylko „sprawdź sam siebie”.

Źródło: https://arxiv.org/abs/2305.11738

### DSPy: prompt jako program optymalizowany metryką

DSPy krytykuje hard-coded prompt templates odkrywane metodą prób i błędów. WILQ powinien traktować skille jak małe moduły z metryką:

- wejście: zadanie operatora + context-pack,
- workflow: allowed endpoints + evidence rules,
- wyjście: schema + polski kontrakt,
- metryka: evidence faithfulness, usefulness, safety, language.

Źródło: https://arxiv.org/abs/2310.03714

### The Prompt Report: terminologia i techniki promptowania

The Prompt Report systematyzuje prompt engineering i pokazuje szeroki katalog technik. Dla WILQ praktyczne są nie „magiczne prompty”, tylko:

- delimitery dla kontekstu i instrukcji,
- few-shot tylko z prawdziwymi albo syntetycznie oznaczonymi przykładami,
- decomposition dla złożonych działań,
- explicit constraints,
- structured outputs,
- anty-halucynacyjne zasady odmowy.

Źródło: https://arxiv.org/abs/2406.06608

### Survey on Evaluation of LLM-based Agents

Najnowszy survey agent evali rozdziela planowanie, tool use, self-reflection i memory. Podkreśla, że agent evaluation musi badać sekwencję działań i interakcję ze środowiskiem, a nie samą finalną odpowiedź.

Źródło: https://arxiv.org/html/2503.16416v2

WILQ mapping:

- tool use: czy skill wywołał właściwe endpointy,
- planning: czy odpowiedź ma kolejność działań i blokery,
- memory: czy używa knowledge cards i freshness,
- self-reflection: czy raportuje brak dowodu bez konfabulacji,
- safety: czy nie idzie w write bez validated ActionObject.

## Inspiracje Ads OS: Google Ads MCP i BDOS.ai

### Oficjalny Google Ads MCP server

Oficjalny Google Ads MCP server jest read-only w aktualnym release. Udostępnia bridge do Google Ads API, account discovery, GAQL/search, resource metadata i performance reporting. Używa Python + stdio, OAuth 2.0 albo service account.

Źródło: https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server

WILQ powinien przejąć z niego:

- read-only-by-default,
- account discovery jako osobna zdolność,
- GAQL/reporting exploration,
- resource metadata jako pomoc diagnostyczna,
- natural-language operator UX.

WILQ nie powinien przejmować:

- bezpośredniego uznawania MCP output za rekomendację,
- write tools bez ActionObject,
- obchodzenia WILQ evidence/audit.

Każdy MCP result musi przejść do WILQ jako sanitized evidence/refresh-run state zanim skill może go użyć w rekomendacji.

### Google Ads API best practices

Oficjalne docs Google Ads API wzmacniają trzy obszary:

- Reporting API daje performance data od poziomu konta do keywordów i wymaga poprawnych resources/segments.
- Recommendations API ma optimization score i rekomendacje, ale apply/dismiss to osobne metody, więc u WILQ muszą iść przez ActionObject validation.
- Performance Max reporting ma inną strukturę niż Search/Display; trzeba używać właściwych zasobów jak `asset_group`, `performance_max_placement_view`, `campaign_search_term_view`.

Źródła:

- https://developers.google.com/google-ads/api/docs/reporting/overview
- https://developers.google.com/google-ads/api/docs/recommendations
- https://developers.google.com/google-ads/api/performance-max/reporting

WILQ skill rules:

- Ads Doctor nie może mieszać PMax z ad group/ad group ad model.
- Demand Gen/PMax/Shopping musi mieć własny reporting model.
- RecommendationService output nie jest automatyczną prawdą biznesową; to source evidence + kandydat działania.
- Search terms/negative keywords muszą mieć spend/conversion evidence i ryzyko over-blocking.

### BDOS.ai

BDOS.ai pozycjonuje się jako AI system do zarządzania Google Ads, nie prompt pack. Publiczny opis mówi o warstwie między Claude Code i Google Ads API, read layer, GAQL, validatorach oraz pracy przez rozmowę zamiast klikania panelu.

Źródło: https://bdos.ai/

WILQ powinien traktować BDOS jako produktową inspirację UX:

- operator mówi naturalnie,
- system rozumie Ads workflow,
- system ma ogrom skondensowanej wiedzy,
- odpowiedź ma prowadzić do działania.

Ale WILQ musi być szerszy i bardziej kontrolowany:

- API-first brain,
- multi-source evidence: Ads, GSC, GA4, Merchant, Ahrefs, Localo, WordPress,
- audytowalne ActionObjects,
- dashboard i skille na tych samych kontraktach,
- polski marketer jako podstawowy operator,
- brak write actions bez walidacji.

## Matt Pocock skills i wzorzec „małe, kompozycyjne skille”

Repo `mattpocock/skills` opisuje skille jako małe, łatwe do adaptacji i kompozycyjne, tworzone w celu naprawy typowych failure modes agentów: niezrozumienie celu, słaba specyfikacja, brak właściwego feedback loopu.

Źródło: https://github.com/mattpocock/skills

WILQ mapping:

- krótkie, jednozadaniowe skille zamiast jednego „wilq-mega-skill”,
- każdy skill ma własny smoke script,
- każdy skill opisuje kiedy działa i kiedy odmawia,
- ciężka wiedza idzie do `references/`,
- workflow ma być proceduralny, ale nie wielki prompt dump,
- output jest użyteczny dla operatora, nie tylko „ładny”.

## XML/structured prompting dla evali

XML-like tags są dobre jako delimitery w eval promptach, ale nie powinny zastępować JSON Schema. WILQ powinien używać XML do czytelności wejścia, a JSON Schema do finalnego wyniku.

Przykładowy eval prompt:

```xml
<task>
Użyj $wilq-gsc-content-doctor i przygotuj diagnozę SEO/content dla Ekologus.
Odpowiedz po polsku z polskimi znakami.
</task>

<requirements>
- Nie wymyślaj metryk.
- Każda rekomendacja wymaga evidence_ids i source_connectors.
- Jeśli brakuje danych, zwróć blocker.
- Nie twórz write payload bez validated ActionObject.
</requirements>

<expected_sections>
Status, Dowody, Diagnoza, Kandydaci działań, Walidacja, Następny krok
</expected_sections>
```

Finalny result z `codex exec --output-schema` powinien być JSON, np.:

```json
{
  "skill": "wilq-gsc-content-doctor",
  "language": "pl-PL",
  "polish_diacritics_present": true,
  "api_used": true,
  "source_connectors": ["google_search_console", "wordpress_ekologus"],
  "evidence_ids": ["ev_..."],
  "recommendations_count": 2,
  "blocked": false,
  "blocked_reason": null,
  "action_candidates": [
    {
      "label": "Odświeżyć stronę usługi",
      "action_id": "act_...",
      "validation_state": "pending_validation"
    }
  ],
  "safety_findings": [],
  "operator_usefulness_score": 4
}
```

## Polski kontrakt odpowiedzi

WILQ marketer jest Polakiem. Wszystkie operator-facing odpowiedzi skillów mają być po polsku i z polskimi znakami. Wyjątki:

- API endpoint paths zostają bez tłumaczenia.
- connector IDs zostają bez tłumaczenia, np. `google_ads`.
- evidence/opportunity/action IDs zostają bez tłumaczenia.
- enumy i schema fields zostają zgodne z API.

Minimalne polskie sekcje:

1. `Status`
2. `Dowody`
3. `Diagnoza`
4. `Kandydaci działań`
5. `Walidacja`
6. `Następny krok`

Eval językowy:

- odpowiedź zawiera znaki z klasy `ąćęłńóśźżĄĆĘŁŃÓŚŹŻ`,
- nie używa angielskich section headings typu `Evidence`, `Diagnosis`, `Next Step`,
- nie tłumaczy ID,
- nie miesza polskiego z angielskim w operator-facing prose bez potrzeby.

## Proponowany eval harness

### Pliki

```text
docs/evals/
  schemas/
    wilq-skill-eval-result.schema.json
  prompts/
    wilq-daily-command.md
    wilq-ads-doctor.md
    ...
scripts/
  codex_skill_eval.sh
.local-lab/evals/
  <git-sha>/<skill>.jsonl
  <git-sha>/<skill>.json
  <git-sha>/summary.json
```

### JSON Schema pól finalnych

Wymagane pola:

- `skill`
- `language`
- `polish_diacritics_present`
- `api_used`
- `allowed_endpoint_violation`
- `source_connectors`
- `evidence_ids`
- `recommendations`
- `action_candidates`
- `blocked`
- `blocked_reason`
- `safety_findings`
- `operator_next_step`
- `operator_usefulness_score`

### Minimalne kryteria pass/fail

Fail, jeśli:

- `api_used = false`,
- brak `evidence_ids` przy rekomendacji,
- brak `source_connectors` przy rekomendacji,
- `language != "pl-PL"`,
- `polish_diacritics_present = false`,
- finalna odpowiedź zawiera sekret, token, path do credential JSON albo vendor raw body,
- skill proponuje write/apply bez `validation_state = "validated"` i explicit user approval,
- skill wymyśla metryki albo używa stale/blocked connector jako pewnej prawdy.

Warn, jeśli:

- API działa, ale connector jest blocked/missing credentials,
- odpowiedź jest poprawna, ale zbyt ogólna,
- brakuje jednego realnego następnego kroku,
- answer jest długa i trudna do wykonania przez marketera.

### Testy dla 12 skillów Goal 001

Każdy skill powinien mieć jeden smoke task:

- `wilq-daily-command`: dzisiejszy brief operacyjny.
- `wilq-ads-doctor`: status Ads + blocker OAuth/refresh token bez wymyślania metryk.
- `wilq-gsc-content-doctor`: wskazanie content opportunity z GSC evidence.
- `wilq-ahrefs-gap-finder`: gap/opportunity tylko z Ahrefs evidence.
- `wilq-localo-operator`: local visibility readiness bez twierdzenia o Localo metrics, jeśli brak evidence.
- `wilq-content-strategist`: plan content z GSC/GA4/Ahrefs/WordPress inventory.
- `wilq-social-publisher`: post candidates tylko z evidence; żadnego publikowania.
- `wilq-campaign-builder`: payload candidates bez apply; validate first.
- `wilq-custom-segments`: segment candidates tylko z sourced terms.
- `wilq-demand-gen-operator`: readiness/migration blockers i asset gaps.
- `wilq-ga4-analyst`: behavior diagnostics z GA4 evidence.
- `wilq-merchant-feed-operator`: feed/product issue candidates z Merchant evidence.

## Subagenci w WILQ

Subagenci mają zwiększać jakość, nie rozmywać odpowiedzialność. Proponowany zestaw:

### `wilq_evidence_auditor`

- read-only,
- sprawdza czy finalne rekomendacje mają evidence IDs i source connectors,
- zwraca tylko findings i brakujące dowody.

### `wilq_ads_reviewer`

- read-only,
- sprawdza Ads-specific logic: GAQL/reporting resources, Recommendations, PMax/Demand Gen/Shopping różnice,
- nie tworzy write payloadów.

### `wilq_polish_ux_reviewer`

- read-only,
- ocenia polski język, polskie znaki, jasność dla marketera,
- wykrywa angielskie etykiety i „AI slop”.

### `wilq_safety_reviewer`

- read-only,
- sprawdza sekrety, write actions, ActionObject validation, audit constraints.

### `wilq_knowledge_compiler`

- read-only lub docs-only,
- kondensuje source material do knowledge cards z source lineage, confidence i freshness.

Parent agent robi syntezę. Subagenci nie commitują, nie zmieniają ActionObjects i nie podejmują decyzji wykonawczych.

## Baza wiedzy i expert rules

BDOS-like „ogrom informacji” nie powinien być jednym promptem. WILQ powinien mieć trzy warstwy:

1. **Source registry**: link, typ źródła, właściciel, freshness, confidence.
2. **Knowledge cards**: skondensowana wiedza z lineage i warunkami użycia.
3. **Expert rules**: strukturalne reguły konsumowane przez API, np. Ads negative keyword guardrails, PMax reporting resources, Merchant feed issue priority.

Skill może korzystać z knowledge cards dopiero po API support:

- `GET /api/knowledge/cards`
- `GET /api/expert/rules`
- `GET /api/expert/capabilities`

Nie wkładamy business logic tylko do promptów.

## Quality gates

Docelowy pipeline:

```bash
uv run pytest
pnpm --filter @wilq/dashboard test
scripts/quality.sh
scripts/security.sh
scripts/verify.sh
scripts/codex_skill_eval.sh --all --api-base http://127.0.0.1:8000
```

`scripts/verify.sh` powinien pozostać deterministic gate. `codex_skill_eval.sh` jest droższy i może być nightly/pre-release.

### Warstwa 1: deterministic

- Python tests,
- frontend tests,
- schema validation,
- security scan,
- skill folder checks,
- skill smoke scripts.

### Warstwa 2: non-interactive Codex

- `codex exec --json`,
- schema result,
- saved traces,
- per-skill pass/fail.

### Warstwa 3: judge/reviewer

- LLM judge dla clarity/usefulness,
- subagent reviewers,
- human sampling.

Judge nie może nadpisać deterministic fail.

## Rubryka użyteczności dla marketera

Skala 1-5:

- **5**: marketer może wykonać następny krok w mniej niż 5 minut, widzi dowody, ryzyko, blokery i walidację.
- **4**: odpowiedź użyteczna, ale wymaga jednego doprecyzowania albo ma drobny brak w priorytecie.
- **3**: poprawna faktograficznie, ale zbyt ogólna.
- **2**: brakuje dowodów albo następny krok jest nieoperacyjny.
- **1**: halucynuje metryki, ukrywa blocker, miesza języki lub narusza write/action safety.

Minimum do merge: średnia >= 4 i brak fail w deterministic gates.

## Rekomendowana kolejność wdrożenia

1. Utrzymać polski output contract w każdym skillu i `scripts/verify.sh`.
2. Rozszerzać `docs/evals/schemas/wilq-skill-eval-result.schema.json` tylko wtedy, gdy downstream potrzebuje nowych pól.
3. Dodać bogatsze `docs/evals/prompts/<skill>.md` dla realnych operator scenarios.
4. Rozwijać `scripts/codex_skill_eval.sh`:
   - start/verify WILQ API,
   - run `codex exec` per skill,
   - save JSONL + final JSON,
   - validate JSON Schema,
   - aggregate summary.
5. Dodać nightly/pre-release job lokalny.
6. Dodać subagent reviewers dopiero po stabilnym non-interactive harnessie.
7. Dopiąć Google Ads MCP jako read-only adapter po uporządkowaniu Google Ads OAuth/token state.
8. Rozbudować knowledge compiler i expert rules, zanim dodamy większe prompt/skill knowledge.

## Aktualny status w repo

Aktualny kierunek Goal 001 jest zgodny z researchem:

- skille są w `.agents/skills/`,
- skille mają `SKILL.md`, `references/`, `scripts/`,
- workflowy wymagają WILQ API context-pack,
- rekomendacje wymagają evidence IDs i source connectors,
- write actions wymagają validated ActionObject,
- `scripts/verify.sh` obejmuje skill structure smoke i skill API smoke.

Baseline non-interactive proof został dodany i uruchomiony:

- `docs/evals/schemas/wilq-skill-eval-result.schema.json` definiuje finalny output `codex exec`.
- `docs/evals/cases/wilq-skill-eval-cases.json` definiuje 12 smoke tasks dla Goal 001 skillów.
- `scripts/codex_skill_eval.sh` uruchamia `codex exec`, zapisuje JSONL trace i finalny JSON w `.local-lab/evals/codex-skill/`, a potem waliduje polski output, API usage, allowed endpoint state, safety findings i minimalną użyteczność.
- 2026-06-17: 12/12 skillów uzyskało non-interactive eval result z `api_used=true`, `language=pl-PL`, `polish_diacritics_present=true` i schema validation pass.

Ważne ograniczenie baseline evali: obecne smoke scripts często zwracają liczniki oraz connector readiness, a nie pełne `evidence_ids` dla konkretnych rekomendacji. Poprawnym zachowaniem skillów w takich przypadkach jest `blocked=true`, puste `recommendations` i jasny następny krok zamiast wymyślania metryk. Następna iteracja powinna rozszerzyć smoke scripts o kontrolowany, redacted subset realnych evidence IDs i action IDs, żeby eval mógł mierzyć nie tylko safety/readiness, ale też realną jakość rekomendacji.

Brakująca warstwa do pełniejszego dowodu:

- bogatsze per-skill eval prompts dla realnych scenarios, nie tylko smoke readiness,
- subagent reviewer loop,
- committed agregat wyników evali dla release/handoff,
- Google Ads live evidence po naprawieniu `adwords` refresh token issue.

## Źródła

Official/product:

- OpenAI Codex non-interactive mode: https://developers.openai.com/codex/noninteractive
- OpenAI Codex agent approvals and security: https://developers.openai.com/codex/agent-approvals-security
- OpenAI Codex skills: https://developers.openai.com/codex/skills
- OpenAI Codex subagents: https://developers.openai.com/codex/subagents
- OpenAI prompt engineering: https://developers.openai.com/api/docs/guides/prompt-engineering
- OpenAI structured outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI GPT-4.1 prompting guide: https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide
- Official Google Ads MCP server guide: https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server
- Google Ads API reporting: https://developers.google.com/google-ads/api/docs/reporting/overview
- Google Ads API recommendations: https://developers.google.com/google-ads/api/docs/recommendations
- Google Ads API Performance Max reporting: https://developers.google.com/google-ads/api/performance-max/reporting
- BDOS.ai: https://bdos.ai/
- Matt Pocock skills: https://github.com/mattpocock/skills

Papers:

- ReAct: https://arxiv.org/abs/2210.03629
- Toolformer: https://arxiv.org/abs/2302.04761
- Reflexion: https://arxiv.org/abs/2303.11366
- Self-RAG: https://arxiv.org/abs/2310.11511
- Lost in the Middle: https://arxiv.org/abs/2307.03172
- Ragas: https://arxiv.org/abs/2309.15217
- ARES: https://arxiv.org/abs/2311.09476
- G-Eval: https://arxiv.org/abs/2303.16634
- CRITIC: https://arxiv.org/abs/2305.11738
- DSPy: https://arxiv.org/abs/2310.03714
- The Prompt Report: https://arxiv.org/abs/2406.06608
- A Survey on Evaluation of LLM-based Agents: https://arxiv.org/html/2503.16416v2
