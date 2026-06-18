## Diagnoza obecnego stanu

Architektura **idzie w dobrym kierunku**: WILQ ma właściwy kręgosłup — FastAPI jako mózg, typed schemas, evidence registry, ActionObjecty, expert rules, dashboard i Codex skills podpięte do tych samych endpointów. To jest znacznie bliżej “marketing operating system” niż prompt pack albo panel connectorów. Product bar trafnie wymusza: evidence IDs, source connectors, blocked claims, brak zmyślonych metryk i ścieżkę `dry_run -> preview -> confirm -> audit`.

Ale obecny produkt jest jeszcze na etapie **safe operating shell**, nie pełnego BDOS-class OS. WILQ umie już dobrze powiedzieć “co wolno twierdzić” i “czego nie wolno twierdzić”, ale za mało często odpowiada: **“co dokładnie mam teraz kliknąć / przejrzeć / przygotować, żeby zarobić lub odzyskać ruch”**.

Największy problem nie jest w liczbie skillsów. Problemem jest to, że **API ma częściowe fakty, a UI/skills czasem próbują z nich zrobić zbyt szeroki produkt**. Najmocniejsze dziś są: Merchant feed review, GA4 tracking/landing quality review, Content refresh queue i safe Ads campaign-level review. Najsłabsze są: Ahrefs gap, Demand Gen, Custom Segments, Localo insight i Campaign Builder — nie dlatego, że skille są źle napisane, tylko dlatego, że brakuje read contracts i ActionObjectów. Ledger sam to potwierdza: 12/12 evale przechodzą, ale część to guardrail pass, nie pełna wartość marketingowa.

Nie uruchamiałem lokalnie API/dashboardu ani `scripts/verify.sh`; audyt opieram na repo, kodzie i ledgerach. Tam, gdzie piszę “verified”, mam na myśli stan zapisany w repo, nie własny runtime run.

---

## Czy dashboard + WILQ API + Codex skills idą w dobrym kierunku?

**Tak, kierunek jest właściwy.** Decyzja “WILQ API jako mózg” jest najlepszą decyzją architektoniczną w repo. `/api/dashboard/command-center`, `/api/marketing/brief`, `/api/marketing/tactical-queue`, `/api/actions` i `/api/codex/context-pack` tworzą sensowną wspólną warstwę dla dashboardu i skillsów. `POST /api/codex/context-pack` ma już skill-scoped tryb, co jest krytyczne, bo pełny context-pack był za duży i za wolny.

**Ale obecna implementacja ma trzy pęknięcia:**

1. **Command Center nadal nie jest wystarczająco “operator-first”.** API zwraca `operator_brief` i `action_plan`, ale równolegle istnieją `marketing_brief.sections`, `tactical_queue.items`, diagnostics sections i ActionObjecty. To daje kilka konkurencyjnych źródeł “co robić teraz”.

2. **Są ślady starego stanu i duplicate meaning.** Ads jest już live campaign-level, a w `ads_action_safety` nadal pojawia się narracja “prepare-only repair action dla OAuth”. To nie powinno trafiać do marketer-facing UI, bo miesza aktualną prawdę z historycznym blockerem.

3. **Performance i koszt kontekstu nadal blokują świetne UX.** Progress ledger pokazuje lokalne pomiary: `/api/dashboard/command-center` około 3.2 s, `/api/codex/context-pack` około 9.15 s i 940 KB przed scoped packiem. Scoped content context-pack spadł do około 2.68 s i 154 KB, więc kierunek działa, ale daily/full context nadal wymaga odchudzenia.

---

## Stop doing

1. **Przestać traktować connector readiness jako insight.** `configured`, `ready for refresh`, `no performance metrics` i podobne stany są diagnostyką systemu, nie decyzją marketera.

2. **Przestać promować social draft ActionObjecty w daily flow.** Social może istnieć tylko w explicit social workflow. Daily Command ma pokazywać Merchant / Content / GA4 / Ads, nie LinkedIn/Facebook.

3. **Przestać rozwijać skillsy przed read contractami.** Ahrefs, Demand Gen, Custom Segments, Campaign Builder i Localo nie staną się użyteczne przez prompt polish. Potrzebują konkretnych endpointów i evidence.

4. **Przestać ładować pełny context-pack jako domyślny runtime.** Full pack jest dobry do debug, nie do codziennej pracy skilla.

5. **Przestać dublować akcje w `marketing_brief`, `tactical_queue`, `action_plan`, diagnostics i globalnym `/api/actions` bez jednego canonical daily view model.**

6. **Przestać zostawiać angielski/operator-unfriendly UI w dashboardzie.** W `App.tsx` są nadal generyczne teksty typu “Loading WILQ API state”, “Missing credentials”, “Configured”, “Evidence”, “Source”. Dla operatora Ekologus to powinno być po polsku i w hierarchii decyzji, nie debug cards.

7. **Przestać mówić “Ads Doctor” jakby był już money-leak optimizer.** Na dziś wolno mówić: live campaign facts. Nie wolno mówić: search-term waste, CPA, ROAS, wasted budget, negative keywords.

---

## Start doing

1. **Wprowadzić `DailyDecision` jako jedyny canonical model Command Center.** Każda decyzja ma mieć: `co_widzimy`, `dlaczego_to_ma_znaczenie`, `bezpieczny_next_step`, `blocked_claims`, `evidence_ids`, `source_connectors`, `action_ids`, `skill_id`, `codex_prompt`, `route`.

2. **Zrobić Command Center jako “3 rzeczy na teraz”, nie dashboard całego systemu.** Pierwszy ekran: Merchant, Content, GA4, Ads jako follow-up. Localo tylko jako blocker/status niżej. Social ukryty, dopóki operator nie pyta o social.

3. **Dodać twardy performance budget.** Command Center summary: <1 s lokalnie i <80–120 KB. Skill context-pack: <2 s i <200 KB dla non-daily. Full context tylko z `full_context=true`.

4. **Podnieść evale z guardrail do usefulness.** Nie wystarczy `api_used=true` i `pl-PL`. Eval ma wymagać konkretnych decyzji, np. Merchant issue clusters, Content `refresh/merge/create/block`, GA4 ranked landing/source rows, Ads blocked-claim matrix.

5. **Dodać read contracts tam, gdzie jest realny marketing money.** Pierwsze: Merchant issue-level, GSC/GA4/WordPress URL matching, Ads search terms + conversions + campaign table. Localo i Ahrefs później.

---

# Najlepsze 5 następnych slice’ów na 4–8 godzin

## Slice 1 — Command Center jako `DailyDecision`, bez slopu i bez duplicate actions

**Cel:**
Pierwszy ekran ma odpowiedzieć: “co mam teraz zrobić?” w 3–5 decyzjach, bez readiness cards, bez social leaków, bez Localo jako primary card.

**Pliki do zmiany:**

* `wilq/briefing/command_center.py`
* `wilq/briefing/marketing_brief.py`
* `apps/api/wilq_api/main.py`
* `packages/shared-schemas/src/index.ts`
* `apps/dashboard/src/routes/App.tsx`
* `tests/test_api_contracts.py`
* `docs/evals/cases/wilq-skill-eval-cases.json`
* `.agents/skills/wilq-daily-command/SKILL.md`

**API contract:**
Dodać do `/api/dashboard/command-center`:

```json
{
  "daily_decisions": [
    {
      "id": "decision_review_merchant_feed_issues",
      "priority": 10,
      "title": "Przejrzyj problemy produktów w Merchant Center",
      "route": "/merchant",
      "what_we_know": "...",
      "why_it_matters": "...",
      "safe_next_step": "...",
      "source_connectors": ["google_merchant_center"],
      "evidence_ids": ["..."],
      "action_ids": ["act_review_merchant_feed_issues"],
      "blocked_claims": ["approval restored", "revenue recovered", "automatic feed edit"],
      "skill_id": "wilq-merchant-feed-operator",
      "codex_prompt": "..."
    }
  ]
}
```

`operator_brief` i `action_plan` mogą zostać jako backward-compatible, ale dashboard i `wilq-daily-command` mają używać `daily_decisions`.

**Dashboard behavior:**
Na first screen:

* hero: `primary_next_step`,
* 3–4 karty decyzji,
* każda karta: “co widzę / co to znaczy / co zrobić teraz / czego nie wolno twierdzić / uruchom w Codex”,
* brak connector grid,
* brak raw `sections={}`,
* brak social draft actions,
* Localo widoczne tylko w “Źródła i blockery”, nie w “do zrobienia teraz”.

**Skill behavior:**
`wilq-daily-command` ma zwracać dokładnie 3–5 decyzji z `daily_decisions`. Nie wolno mu agregować `marketing_brief.action_ids`, jeżeli nie są daily-core.

**Test/eval proof:**

* test API: `daily_decisions` zawiera tylko core actions:

  * `act_review_merchant_feed_issues`,
  * `act_prepare_content_refresh_queue`,
  * `act_review_ga4_tracking_quality`,
  * opcjonalnie Ads review bez action.
* test negatywny: brak `act_prepare_linkedin_social_drafts`, brak `act_prepare_facebook_social_drafts`.
* eval daily: wymaga `what_we_know`, `why_it_matters`, `safe_next_step`, `blocked_claims`, `route`.
* browser proof: first screen nie zawiera “configured”, “ready for refresh”, “No performance metrics”.

**Ryzyka:**
Można za mocno ukryć prawdziwe blockery. Rozwiązanie: osobna sekcja “Źródła i blockery” pod foldem, ale nie w primary decisions.

---

## Slice 2 — Performance: odchudzić context-pack i first-screen fetch

**Cel:**
Zbić daily latency i payload, bo obecny full context-pack był około 940 KB / 9 s, a Command Center około 3.2 s. Scoped context już udowodnił poprawę, więc trzeba ten wzorzec dokończyć.

**Pliki do zmiany:**

* `apps/api/wilq_api/main.py`
* nowy `wilq/codex/context_pack.py`
* `wilq/briefing/command_center.py`
* `apps/dashboard/src/lib/api.ts`
* `apps/dashboard/src/routes/App.tsx`
* `tests/test_api_contracts.py`
* opcjonalnie `scripts/perf_probe.py` albo istniejący verify/perf smoke

**API contract:**

`POST /api/codex/context-pack`:

```json
{
  "skill": "wilq-ads-doctor",
  "view": "summary",
  "max_evidence": 40,
  "full_context": false
}
```

Response powinien mieć:

```json
{
  "context_scope": {
    "mode": "skill",
    "skill": "wilq-ads-doctor",
    "view": "summary",
    "source_connectors": ["google_ads"],
    "omitted_sections": ["marketing_brief", "tactical_queue"]
  },
  "payload_budget": {
    "max_evidence": 40,
    "full_context_available": true
  }
}
```

**Dashboard behavior:**
`/command-center` fetchuje tylko `/api/dashboard/command-center` na first screen. `marketing/brief`, `tactical-queue`, actions i diagnostics są lazy-loaded po wejściu w route albo rozwinięciu szczegółów. React Query dostaje sensowny `staleTime`, np. 60 s dla read-only view modeli.

**Skill behavior:**
Każdy non-daily skill używa scoped packa. Daily może używać daily summary pack, a full context tylko gdy operator prosi o debug.

**Test/eval proof:**

* test JSON size: scoped pack <200 KB dla non-daily,
* test full pack nie jest defaultem,
* test Command Center nie odpala pełnego tactical queue, jeśli nie potrzebuje szczegółów,
* `scripts/codex_skill_eval.sh --all` nadal przechodzi.

**Ryzyka:**
Za mało evidence w scoped packu może obniżyć jakość odpowiedzi. Dlatego response musi mówić `full_context_available=true` i mieć kontrolowany fallback.

---

## Slice 3 — Merchant issue-level triage jako najmocniejszy demo win

**Cel:**
Zrobić z Merchant realną kolejkę pracy, nie tylko “products=10900, issues=15”. To jest dziś najlepszy kandydat na marketer value, bo ma live facts i konkretny ActionObject. Ledger potwierdza `product_count=10900`, `issue_count=15` i `act_review_merchant_feed_issues`.

**Pliki do zmiany:**

* `wilq/briefing/merchant_diagnostics.py`
* `wilq/actions/service.py`
* connector Merchant client, jeśli issue details są już dostępne:

  * `wilq/connectors/google_merchant_center/client.py`
* `wilq/storage/metric_store.py`, jeśli trzeba utrwalić issue dimensions
* `packages/shared-schemas/src/index.ts`
* `apps/dashboard/src/routes/App.tsx`
* `.agents/skills/wilq-merchant-feed-operator/SKILL.md`
* merchant smoke script
* `docs/evals/cases/wilq-skill-eval-cases.json`
* `tests/test_api_contracts.py`

**API contract:**

`GET /api/merchant/diagnostics` dodaje:

```json
{
  "issue_clusters": [
    {
      "id": "merchant_issue_missing_image_link",
      "issue_type": "missing_image",
      "severity": "DISAPPROVED",
      "affected_attribute": "image_link",
      "product_count": 3,
      "sample_product_ids": ["..."],
      "sample_titles": ["..."],
      "source_connectors": ["google_merchant_center"],
      "evidence_ids": ["..."],
      "blocked_claims": ["approval restored", "revenue recovered"],
      "action_id": "act_review_merchant_feed_issues"
    }
  ]
}
```

ActionObject payload:

```json
{
  "review_queue": [
    {
      "issue_cluster_id": "merchant_issue_missing_image_link",
      "review_mode": "read_only",
      "suggested_operator_check": "Sprawdź image_link w feedzie przed zmianą."
    }
  ],
  "external_write": false
}
```

**Dashboard behavior:**
Route `/merchant` pokazuje:

* licznik produktów i issue count,
* klastry problemów,
* próbki produktów,
* przycisk “Waliduj ActionObject”,
* jasne “to nie naprawia feedu automatycznie”.

**Skill behavior:**
`wilq-merchant-feed-operator` ma:

* pogrupować issue clusters,
* wskazać 1. najbezpieczniejszy review queue,
* wywołać walidację `act_review_merchant_feed_issues`,
* zablokować approval/revenue recovery.

**Test/eval proof:**

* test seeduje issue-level facts i oczekuje `issue_clusters`.
* eval wymaga `issue_type`, `affected_attribute`, `product_count`, `action_id`, `validation_state`.
* negatywny test: skill nie może twierdzić, że naprawił feed.

**Ryzyka:**
Merchant API może nie zwrócić wystarczających sample product details w aktualnym readzie. Wtedy pierwszy etap robi klastry z dostępnych dimensions, a product samples pokazuje jako “brak w obecnym read contract”.

---

## Slice 4 — Content/GA4/GSC/WordPress URL normalizer i realna kolejka `refresh/merge/create/block`

**Cel:**
Naprawić lukę `matched_inventory_count=0`. Bez normalizacji URL-i WILQ nie wie, czy ma odświeżyć istniejącą treść, stworzyć nową, połączyć duplikaty czy zablokować zadanie. To bezpośrednio ogranicza wartość Content Planner i GSC skills.

**Pliki do zmiany:**

* nowy `wilq/content/url_normalizer.py`
* `wilq/briefing/content_diagnostics.py`
* `wilq/briefing/ga4_diagnostics.py`
* `wilq/briefing/tactical_queue.py`
* WordPress connector client
* `packages/shared-schemas/src/index.ts`
* `apps/dashboard/src/routes/App.tsx`
* `.agents/skills/wilq-content-strategist/SKILL.md`
* `.agents/skills/wilq-gsc-content-doctor/SKILL.md`
* `.agents/skills/wilq-ga4-analyst/SKILL.md`
* `tests/test_api_contracts.py`
* eval cases dla content/GSC/GA4

**API contract:**

`GET /api/content/diagnostics` dodaje:

```json
{
  "content_candidates": [
    {
      "id": "content_candidate_zielony_lad_refresh",
      "decision": "refresh",
      "canonical_url": "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
      "query": "zielony ład",
      "wp_match_state": "matched",
      "reason": "GSC query/page ma evidence i WordPress inventory potwierdza istniejący URL.",
      "source_connectors": ["google_search_console", "wordpress_ekologus"],
      "evidence_ids": ["..."],
      "blocked_claims": ["ranking guarantee", "lead uplift", "revenue impact"],
      "action_ids": ["act_prepare_content_refresh_queue"]
    }
  ]
}
```

`GET /api/ga4/diagnostics` dodaje `landing_candidates[]` z `wp_match_state` i `tracking_gap_reason`.

**Dashboard behavior:**
`/content-planner` pokazuje cztery koszyki:

* `refresh`,
* `merge`,
* `create_after_inventory_check`,
* `block`.

`/ga4` pokazuje, czy landing problem jest content taskiem, tracking taskiem czy blockerem typu `(not set)`.

**Skill behavior:**
Content/GSC skills mają zwracać konkretne URL-e i decyzje. GA4 skill ma blokować GA4 `(not set)` jako content recommendation i kierować do tracking review.

**Test/eval proof:**

* test URL normalizer dla:

  * trailing slash,
  * http/https,
  * www/non-www,
  * query params,
  * GA4 landing path vs WordPress full URL.
* eval content wymaga min. jednej decyzji `refresh` i jednej `block`.
* eval GSC wymaga konkretnego query/page candidate.
* eval GA4 wymaga rozdzielenia tracking gap vs content task.

**Ryzyka:**
Fałszywe dopasowanie URL może stworzyć duplikację treści. Lepiej zwrócić `create_after_inventory_check` niż automatycznie `create`.

---

## Slice 5 — Ads Doctor: campaign table + search-term read contract / blocker matrix

**Cel:**
Ads jest strategicznie najważniejszy dla “money leak”, ale dziś WILQ ma tylko campaign-level facts. Następny slice ma zrobić uczciwy most: albo prawdziwe search-term evidence, albo bardzo czytelny blocker matrix. Ads skill już ma dobry trigger contract, ale API nie ma jeszcze danych dla jego najważniejszych pytań.

**Pliki do zmiany:**

* `wilq/connectors/google_ads/client.py`
* `wilq/briefing/ads_diagnostics.py`
* `wilq/actions/service.py`
* `packages/shared-schemas/src/index.ts`
* `apps/dashboard/src/routes/App.tsx`
* `.agents/skills/wilq-ads-doctor/SKILL.md`
* ads smoke script
* `docs/evals/cases/wilq-skill-eval-cases.json`
* `tests/test_api_contracts.py`

**API contract:**

`GET /api/ads/diagnostics` dodaje:

```json
{
  "campaign_rows": [
    {
      "campaign_id": "...",
      "campaign_name": "...",
      "status": "...",
      "clicks": 3,
      "impressions": 123,
      "cost_micros": 123456,
      "evidence_ids": ["..."]
    }
  ],
  "read_contracts": {
    "campaign_overview": "ready",
    "search_terms": "missing",
    "conversion_metrics": "missing",
    "recommendations": "missing",
    "impression_share": "missing"
  },
  "blocked_claim_matrix": [
    {
      "claim": "wasted budget",
      "status": "blocked",
      "missing_evidence": ["search_term_view.cost_micros", "conversions"]
    }
  ]
}
```

Jeżeli search terms wejdą:

```json
{
  "search_term_rows": [
    {
      "search_term": "...",
      "campaign_id": "...",
      "ad_group_id": "...",
      "clicks": 10,
      "cost_micros": 5000000,
      "conversions": 0,
      "period": "last_90_days",
      "evidence_ids": ["..."]
    }
  ],
  "action_ids": ["act_prepare_negative_keyword_review"]
}
```

**Dashboard behavior:**
`/ads-doctor` pokazuje:

* “co wolno powiedzieć”: campaign table,
* “czego nie wolno powiedzieć”: CPA/ROAS/search terms/waste,
* “czego brakuje”: read contracts,
* jeżeli search terms są gotowe: prepare-only negative keyword review, nie apply.

**Skill behavior:**
`wilq-ads-doctor` ma zwracać ranked campaign table i blocked-claim matrix. Jeśli search terms nie istnieją, żadnych negative keywords. Jeśli istnieją, tylko review candidate z evidence i validation.

**Test/eval proof:**

* test dla current state: live campaign facts, search terms/CPA/ROAS/waste blocked.
* test seeded search terms: `act_prepare_negative_keyword_review` tylko przy koszt + zero conversions + okres ochronny.
* eval Ads wymaga “campaign table + blocked claims matrix”.

**Ryzyka:**
GAQL field compatibility i MCC/child account mogą powodować błędy. Dlatego najpierw explicit query contract + walidator, nie prompt-generated GAQL.

---

# Priorytet napraw skillsów

## P0 — `wilq-daily-command`

To jest skill demo i codzienny operator. Ma największy wpływ na odczucie produktu. Naprawić najpierw:

* używanie `daily_decisions`, nie szerokiego `marketing_brief.action_ids`,
* brak social draft leakage,
* dokładnie 3–5 decyzji,
* każda decyzja ma `what_we_know`, `why_it_matters`, `safe_next_step`, `blocked_claims`, `route`, `evidence_ids`, `action_ids`.

## P0 — `wilq-merchant-feed-operator`

Największy realny win na dziś, bo ma live Merchant facts i ActionObject. Dodać issue-level clustering i validation proof. To powinien być główny demo moment.

## P1 — `wilq-content-strategist` + `wilq-gsc-content-doctor`

Te skille są już blisko wartości, ale muszą przestać być generyczne. Wymagają konkretnych URL-i i decyzji `refresh/merge/create/block`. Największy blocker: WordPress inventory matching.

## P1 — `wilq-ga4-analyst`

Dobry guardrail, ale potrzebuje ranked landing/source/campaign diagnostic items. Musi rozdzielać: tracking gap, weak landing match, content candidate, campaign/source issue.

## P1 — `wilq-ads-doctor`

Wysoka wartość biznesowa, ale nie ma jeszcze search terms / CPA / ROAS / wasted budget evidence. Najpierw campaign table + blocked-claim matrix, potem search-term read contract.

## P2 — `wilq-localo-operator`

Nie naprawiać promptem. Najpierw Localo diagnostics/read contract: rankings, GBP, competitors, reviews. Do tego czasu Localo jest access-ready blocker skill, nie lokalny SEO advisor.

## P2 — `wilq-custom-segments`

Nie ma source terms. Bez Ads search terms, Keyword Planner, GSC query clusters albo competitor terms skill ma słusznie blokować.

## P2 — `wilq-campaign-builder`

Nie ma campaign-specific ActionObject, payload preview, budget, assets, keywords ani targeting. Ma pozostać blockerem do czasu kampanijnego action contractu.

## P3 — `wilq-ahrefs-gap-finder`

Ahrefs aggregate authority nie daje jeszcze content/backlink gap. Potrzebuje competitor pages, backlink gap, content gap, referring domains, URL/query comparisons.

## P3 — `wilq-demand-gen-operator`

Za mało Demand Gen-specific evidence: assets, creative inventory, campaign type, landing quality, migration constraints.

## P3 — `wilq-social-publisher`

Zostawić jako explicit workflow. Nie primary daily. Ma dobrze blokować publikację bez uprawnień.

---

# Jakie dane trzeba jeszcze pozyskać, żeby marketer miał realny zysk

## Google Ads

Priorytetowo:

* `campaign` / `ad_group` rows: status, budget, bidding strategy, campaign type, channel type, final URLs.
* `metrics`: cost, clicks, impressions, CTR, avg CPC, conversions, conversion value, all conversions.
* `search_term_view`: search term, campaign, ad group, keyword context, match type, cost, clicks, conversions, conversion value, 30/90-day windows.
* `keyword_view`: quality score, expected CTR, landing page experience, ad relevance.
* recommendations + optimization score.
* impression share lost to budget/rank.
* change events.
* PMax/product performance joined to Merchant item IDs where possible.
* conversion action status and conversion lag/readiness.

Bez tego Ads nie może uczciwie mówić o CPA, ROAS, wasted budget, negative keywords ani scaling.

## GA4

Potrzebne:

* sessions, users, engaged sessions, engagement rate, average engagement time,
* landing page + source/medium + campaign mapping,
* key events/conversions by landing/source/campaign,
* ecommerce revenue/purchases, jeśli sklep ma e-commerce tracking,
* path/funnel events dla leadów,
* `(not set)` / missing UTM / tracking gap records,
* period deltas 7/28/90 dni,
* join do Ads campaign IDs/names i WordPress URLs.

Bez tego GA4 zostaje “behavior/tracking review”, nie profitability analyst.

## GSC

Potrzebne:

* query + page + device + country + date,
* clicks, impressions, CTR, average position,
* rolling windows: 7/28/90 dni,
* decay, near-top, low CTR,
* cannibalization: jedna fraza → wiele URL-i,
* query clustering,
* normalized URL join do WordPress inventory,
* page freshness/modified date.

Bez tego Content Planner nie rozstrzygnie dobrze refresh vs merge vs create.

## Merchant Center

Potrzebne:

* product status by item ID,
* issue type, severity, affected attribute, resolution, destination/context,
* sample products per issue cluster,
* product title, brand, category, GTIN/MPN, price, sale price, availability, image link, product link,
* feed/data source state,
* expiring products,
* join do Ads/PMax/Shopping product performance,
* custom labels/margins proxy, jeśli dostępne.

Bez issue-level clustering Merchant daje tylko “jest problem”, nie “co przejrzeć pierwsze”.

## Ahrefs

Potrzebne:

* competitors,
* organic keywords,
* top pages,
* content gap,
* keyword gap,
* backlink gap,
* referring domains,
* lost/gained backlinks,
* anchor text,
* DR/UR per URL,
* keyword difficulty, volume, traffic potential,
* SERP overview,
* site audit issues.

Bez tego Ahrefs skill powinien blokować gap claims.

## WordPress

Potrzebne:

* pełny inventory pages/posts/products,
* URL, slug, canonical, title, meta title/description,
* status, publish date, modified date,
* taxonomy/categories/tags,
* content type,
* word count/content length,
* internal links,
* featured image,
* schema/Yoast/RankMath fields, jeśli dostępne,
* redirects/canonical duplicates,
* normalized URL mapping dla GSC i GA4.

Bez tego WILQ będzie tworzył nowe treści zamiast odświeżać lub scalać istniejące.

## Localo

Potrzebne:

* locations/GBP profiles,
* tracked keywords,
* ranking by keyword/location/date/grid,
* GBP visibility vs competitors,
* competitor list and ranking gaps,
* reviews: rating, count, unanswered reviews, sentiment markers if available,
* GBP tasks/profile completeness,
* posts/photos/categories,
* local visibility trend.

Bez tego Localo ma być tylko access/readiness, nie rekomendacje lokalnego SEO.

---

# Acceptance gate dla demo marketera

Demo przechodzi tylko, jeżeli:

1. **Command Center first screen pokazuje 3–5 decyzji, nie status systemu.** Pierwsza decyzja powinna być Merchant feed review, jeżeli `issue_count > 0`. Localo nie jest primary card, social nie jest daily action.

2. **Każda decyzja ma:**

   * source connectors,
   * evidence IDs,
   * ActionObject ID lub jawny blocker,
   * blocked claims,
   * safe next step,
   * Codex skill prompt.

3. **Brak zmyślonych claims:**

   * Ads: CPA/ROAS/search terms/wasted budget blocked, dopóki nie ma read contractów.
   * Localo: ranking/GBP/competitor/local visibility blocked.
   * Social: publishing blocked bez credentials/validation.
   * Content: no ranking/lead/revenue promise.
   * Merchant: no approval/revenue recovery promise.

4. **Dashboard i skill mówią to samo.** Dla promptów:

   * “Pokaż 3 najważniejsze decyzje marketingowe na dziś dla Ekologus.”
   * “Czy Merchant ma problem z produktami/feedem?”
   * “Co w Ads mogę uczciwie powiedzieć?”
   * “Którą treść odświeżyć albo zablokować?”
   * “Czy Localo daje ranking/GBP insight?”

   Codex skill musi zwrócić te same evidence/action IDs co API/dashboard.

5. **Core ActionObject validation działa:**

   * `act_review_merchant_feed_issues`,
   * `act_prepare_content_refresh_queue`,
   * `act_review_ga4_tracking_quality`.

   Brak external write bez preview/confirm/audit.

6. **Performance gate:**

   * `/api/dashboard/command-center` summary <1 s lokalnie,
   * daily context-pack <250 KB i <2.5 s,
   * non-daily scoped context-pack <200 KB i <2 s,
   * full context tylko explicit debug.

7. **Test gate:**

   * `scripts/verify.sh` pass,
   * `scripts/codex_skill_eval.sh --skill wilq-daily-command`,
   * `--skill wilq-merchant-feed-operator`,
   * `--skill wilq-ga4-analyst`,
   * `--skill wilq-content-strategist`,
   * `--skill wilq-ads-doctor`,
   * wszystkie bez endpoint violation i bez safety findings.

8. **Język gate:** first screen i skill outputs po polsku z polskimi znakami. Stable IDs zostają bez tłumaczenia.

Najważniejsza decyzja na teraz: **nie rozbudowywać szeroko dashboardu. Najpierw zrobić Command Center jako prawdziwy DailyDecision cockpit i podnieść Merchant/Content/GA4/Ads do konkretnych, zwalidowanych decyzji.**
