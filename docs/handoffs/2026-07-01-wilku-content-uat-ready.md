# Wilku Content UAT - przygotowanie sesji

Data przygotowania: 2026-07-01
Ostatnia aktualizacja: 2026-07-02 09:55 CEST

Status: gotowe do pokazania jako sesja review/blokad i traceability, nie jako
ukończony UAT.

Zacznij od krótkiej instrukcji:
`docs/handoffs/2026-07-02-co-pokazac-wilkowi.md`. Ten dokument poniżej jest
szczegółowym zapleczem i formatem zapisu wyniku, nie pierwszą rzeczą do
czytania na głos.

Aktualizacja po rozdzieleniu review actions: UAT packet pokazuje teraz osobno
publiczne review actions dla kart usług i prywatne review actions z
`ekologus-ai`. Wynik sesji musi odpowiedzieć na oba pytania, bo publiczne karty
usług nadal blokują production-depth tak samo realnie jak prywatne propozycje.

Aktualizacja po policy proposals: prywatne review actions są teraz rozdzielone
na propozycje usługowe i claim-policy. Live packet pokazuje 4 prywatne review
actions: 2 service oraz 2 policy (`ekologus_claim_policy_brand_voice`,
`ekologus_claim_policy_legal_safety`). Wynik sesji musi osobno odpowiedzieć,
czy policy review actions są czytelne, bo to one mają później pilnować tonu,
poufności i legal-safety, ale nadal nie są automatyczną bramką produkcyjną.

Aktualizacja po live refreshu: 2026-07-01 22:39 UTC. WILQ odświeżył stale
źródła Merchant/Ahrefs/WordPress sklep, więc ten handoff nie zakłada już, że
content/merchant są zablokowane przez nieświeże dane. Pełny UAT nadal jest
zablokowany przez brak production-depth Service Profile, review publicznych
kart usług i review prywatnych propozycji.

Aktualizacja po hardeningu Claim Ledger: claimy oznaczone jako
`allowed_with_evidence` muszą mieć teraz nie tylko `evidence_ids`, ale też
`source_connectors`. Brak źródła danych blokuje gotowość szkicu przez
`missing_source_connector`. Dzięki temu pytanie "skąd to wzięło?" nie kończy
się samym technicznym ID dowodu, tylko prowadzi do konkretnego źródła danych.

Aktualizacja po Sales Brief provenance: UAT packet, recorder wyniku UAT i
completion guard zapisują teraz Sales Brief gate dla wybranego work itemu.
Aktualny live packet pokazuje, że dwa zablokowane itemy nie mają jeszcze
snapshotu Sales Brief, a jedyny actionable item
`content_work_item_content_decision_https___www_ekologus_pl` blokuje Sales
Brief przez: `Brakuje karty usługi; Brakuje karty CTA`. To jest materiał do
review z Wilkiem, nie dowód ukończonego UAT.

Aktualizacja po policy handoff: osobny materiał review dla prywatnych claim
policy proposals z `ekologus-ai` jest w
`docs/handoffs/2026-07-02-wilku-ekologus-ai-policy-review.md`. Pokazuje styl
marki i legal-safety jako redacted review-required proposals, nie jako
zatwierdzoną politykę.

Źródło live:

```bash
rtk uv run python .agents/skills/wilq-content-operator/scripts/build_uat_packet.py --api-base http://127.0.0.1:8000 --limit 3 --format markdown
```

Ostatnie sprawdzenie skilla:

```bash
rtk uv run python .agents/skills/wilq-content-operator/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
```

Wynik ostatniego smoke: `candidate_count=3`, `actionable_candidate_count=1`,
`queue_status=blocked`, `uat_queue_ready=true`, `workflow_blocked=true`,
wybrany work item:
`content_work_item_content_decision_https___www_ekologus_pl`.

## Co sprawdzamy

Cel sesji: sprawdzić, czy Wilku rozumie aktualny stan WILQ bez tłumaczenia
przez developera:

- dlaczego pełny content UAT jest jeszcze zablokowany;
- czy Service Profile jasno pokazuje luki wiedzy i review-required źródła;
- czy publiczne karty usług do review są czytelne jako decyzje właściciela,
  a nie jako zatwierdzona wiedza;
- czy prywatne propozycje z `ekologus-ai` są czytelne jako materiał do review,
  a nie jako zatwierdzona wiedza;
- czy przy obecnej kolejce Wilku umie wskazać bezpieczny następny krok;
- czy na pytanie "skąd to wzięło?" widzi evidence IDs i source connectors;
- czy rozumie, że claim z dowodem bez źródła danych jest teraz blokowany, a nie
  przepychany do szkicu.
- czy rozumie, dlaczego Sales Brief dla wybranego itemu jest zablokowany przez
  brak karty usługi i CTA, a nie przez awarię modelu.

## Aktualny stan WILQ

UAT readiness:

- status: `blocked_for_full_uat`;
- zakres, który można uczciwie pokazać: review/blokady i traceability;
- blokady pełnej sesji: Service Profile nie jest production-depth, publiczne
  karty usług wymagają review Wilka/ownera, prywatne propozycje wymagają review
  Wilka/ownera, kolejka content workflow ma status `blocked`;
- liczba gotowych kandydatów w kolejce: 1.
- kolejka: `candidate_count=3`, `actionable_candidate_count=1`,
  `queue_status=blocked`.
- świeże proof IDs po odświeżeniu źródeł:
  `refresh_google_merchant_center_a04a45a6e6fd`,
  `refresh_ahrefs_5eee21244cff`,
  `refresh_wordpress_sklep_c1db9b8fa677`.
- live Sales Brief gate dla wybranego actionable itemu:
  `selected_sales_brief_status=blocked`, blockery `Brakuje karty usługi` i
  `Brakuje karty CTA`.

Service Profile:

- endpoint: `GET /api/content/service-profile`;
- tryb: read-only;
- production-depth: false;
- status: źródła są, wymagają review;
- następny krok: przejrzeć karty review-required i luki usługowe z Wilkiem
  przed użyciem ich jako production-depth.

Luki do omówienia:

- `gap_no_approved_current_cards`: brak zatwierdzonych production-depth kart
  usług.

Public service review actions:

- `service_profile_review_card_ekologus_service_environmental_consulting_outsourcing`:
  sprawdzić kartę Doradztwo i outsourcing środowiskowy;
- `service_profile_review_card_ekologus_service_bdo_reporting`:
  sprawdzić kartę BDO i sprawozdawczość środowiskowa;
- `service_profile_review_card_ekologus_service_waste_packaging_obligations`:
  sprawdzić kartę Odpady, opakowania i ewidencja środowiskowa;
- `service_profile_review_card_ekologus_service_environmental_training`:
  sprawdzić kartę Szkolenia środowiskowe;
- `service_profile_review_card_ekologus_service_remediation_monitoring`:
  sprawdzić kartę Rekultywacje, remediacje i monitoring;
- `service_profile_review_card_ekologus_service_operat_wodnoprawny`:
  sprawdzić kartę Operaty i pozwolenia wodnoprawne.

Każda z tych akcji ma ten sam warunek bezpieczeństwa: to nie promuje source
fact ani knowledge card; potrzebna jest osobna zatwierdzona akcja i audyt.

Wynik public service review można zapisać osobnym, fail-closed raportem:

```bash
rtk uv run python scripts/record_service_profile_review_result.py .local-lab/proof/service-profile-review-result-YYYYMMDD.json --api-base http://127.0.0.1:8000 --format markdown
```

Minimalny format wyniku review:

```json
{
  "data_review": "YYYY-MM-DD",
  "reviewer": "Wilku",
  "scope_label": "publiczne karty usług Service Profile",
  "decisions": [
    {
      "action_id": "service_profile_review_card_ekologus_service_bdo_reporting",
      "target_card_id": "ekologus_service_bdo_reporting",
      "decision": "approve",
      "source_trace_clear": "tak",
      "blocked_claims_reviewed": "tak",
      "notes": "co Wilku zatwierdził albo co wymaga zmiany"
    }
  ],
  "follow_up_beads": []
}
```

Ten raport nie promuje kart do `approved_current`. Jeżeli decyzja brzmi
`approve`, następny krok to osobny, audytowany promotion request.

Private review actions:

- `service_profile_review_private_proposal_ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01`:
  sprawdzić prywatną propozycję Eko-Opieka / Eko Kalendarz;
- `service_profile_review_private_proposal_ekologus_ai_kb003_audyt_zgodnosci_review_candidate_2026_07_01`:
  sprawdzić prywatną propozycję Audyt zgodności środowiskowej;
- `service_profile_review_private_proposal_ekologus_ai_kb014_brand_voice_review_candidate_2026_07_01`:
  sprawdzić prywatną politykę stylu marki i języka Ekologus;
- `service_profile_review_private_proposal_ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01`:
  sprawdzić prywatną politykę bezpieczeństwa prawnego, poufności i zgód.

Wszystkie te akcje mają ten sam warunek bezpieczeństwa: to nie promuje private
proposal do source fact ani knowledge card.

Wynik private proposal review można zapisać tym samym fail-closed recorderem,
ale z trybem `private_source_proposals`:

```json
{
  "review_type": "private_source_proposals",
  "data_review": "YYYY-MM-DD",
  "reviewer": "Wilku",
  "scope_label": "prywatne propozycje ekologus-ai",
  "decisions": [
    {
      "action_id": "service_profile_review_private_proposal_ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01",
      "target_card_id": "ekologus_service_eko_opieka_calendar",
      "decision": "approve",
      "source_trace_clear": "tak",
      "blocked_claims_reviewed": "tak",
      "notes": "co Wilku zatwierdził albo co wymaga zmiany"
    }
  ],
  "follow_up_beads": []
}
```

Ten raport nadal nie promuje private proposal do source fact ani knowledge card.
Jeżeli decyzja brzmi `approve`, następny krok to osobny, audytowany private
source promotion request.

Promotion checklist dla private proposals:

- status: `promotion_ready=false`;
- powód blokady: brak zatwierdzenia człowieka i reviewed source fact;
- przed reviewed source fact Wilku/owner musi potwierdzić realną ofertę,
  zgodzić się na redacted/source-safe fact, wskazać claimy dozwolone,
  review-required i zakazane, a WILQ musi zapisać reviewer/freshness/confidence/
  lineage oraz przejść focused eval.

Redacted proposal details do sprawdzenia:

- Eko-Opieka / Eko Kalendarz: `review_required`, support `partial`, risk
  `medium`, promotion allowed `false`; zablokowane claimy obejmują obietnicę
  stałej zgodności i gwarancję wykonania obowiązków bez danych klienta.
- Audyt zgodności środowiskowej: `review_required`, support `partial`, risk
  `medium`, promotion allowed `false`; zablokowane claimy obejmują gwarancję
  braku kar i wiążącą ocenę zgodności bez review eksperta.
- Styl marki i język Ekologus: `review_required`, support `direct`, risk
  `high`, promotion allowed `false`; zablokowane claimy obejmują puste slogany,
  gwarantowany wynik i pełną interpretację prawną w darmowej treści.
- Bezpieczeństwo prawne, poufność i zgody: `review_required`, support `direct`,
  risk `high`, promotion allowed `false`; zablokowane claimy obejmują poufne
  dane klientów, gwarantowany wynik administracyjny i pełną interpretację
  prawną bez review człowieka.

Materiał do pokazania przy policy review:

- `docs/handoffs/2026-07-02-wilku-ekologus-ai-policy-review.md`

## Kandydaci z kolejki

### Zablokuj braki w pomiarze GA4 jako zadania contentowe

- work item: `content_work_item_content_decision_ga4_tracking_gap_block`;
- tryb: `block`;
- dowody:
  `ev_refresh_refresh_google_analytics_4_5ebc4ba1c966`,
  `ev_refresh_refresh_google_analytics_4_33a4b3fda0db`;
- source connector: `google_analytics_4`;
- final canonical: brak;
- pytanie do Wilka: czy to jest zrozumiałe jako problem pomiaru, a nie temat
  do pisania?

### Ahrefs: zweryfikuj luki SEO przed planem treści

- work item: `content_work_item_content_decision_ahrefs_gap_records_review`;
- tryb: `block`;
- dowody:
  `ev_refresh_refresh_ahrefs_5eee21244cff`,
  `ev_refresh_refresh_ahrefs_3155c5fa77cf`;
- source connector: `ahrefs`;
- final canonical: brak;
- pytanie do Wilka: czy blocker duplikacji/canonical jasno zatrzymuje pisanie?

### SEO: odśwież lub scal "ekologus" (24 zapytania)

- work item: `content_work_item_content_decision_https___www_ekologus_pl`;
- tryb: `refresh`;
- status: gotowe do planu;
- dowody:
  `ev_refresh_refresh_google_search_console_9b25d4143bea`,
  `ev_refresh_refresh_wordpress_ekologus_691cbe6ab27d`;
- source connectors: `google_search_console`, `wordpress_ekologus`;
- final canonical: `https://www.ekologus.pl/`;
- pytanie do Wilka: czy przy takim temacie WILQ powinien przygotować plan
  odświeżenia strony głównej, czy to jest zbyt szeroki kandydat na pierwszy
  content UAT?
- Sales Brief gate: zablokowany przez `Brakuje karty usługi` i `Brakuje karty
  CTA`. To znaczy: WILQ widzi źródła i kandydat refresh, ale nie ma jeszcze
  zatwierdzonej wiedzy usługowej/CTA, żeby zrobić pełny brief bez generycznego
  SEO.

## Pytania do Wilka

Zadaj dokładnie te pytania i wpisz odpowiedzi w sekcji wyników:

1. Czy rozumiesz, dlaczego pełny content UAT jest teraz zablokowany?
2. Który blocker jest najbardziej sensowny, a który brzmi technicznie?
3. Czy Service Profile mówi Ci, czego brakuje w wiedzy Ekologus?
4. Czy public service review actions dla kart usług są czytelne?
5. Która publiczna karta usługi jest najbardziej niejasna do zatwierdzenia?
6. Czy private service review actions dla Eko-Opieki i Audytu zgodności są
   czytelne?
7. Czy private policy review actions dla stylu marki i legal-safety są czytelne?
8. Czy widzisz, że publiczne karty i prywatne propozycje nie są jeszcze
   zatwierdzoną wiedzą?
9. Gdy pytasz "skąd to wzięło?", czy evidence IDs i source connectors są
   wystarczające?
10. Czy blokada `missing_source_connector` jest zrozumiała po ludzku jako "brak
   źródła danych dla twierdzenia"?
11. Czy `https://www.ekologus.pl/` jako kandydat refresh ma dla Ciebie sens, czy
   lepiej wymusić bardziej konkretny temat, np. BDO?
12. Czy blokada Sales Brief `Brakuje karty usługi; Brakuje karty CTA` jest
   zrozumiała jako brak zatwierdzonej wiedzy, czy brzmi technicznie?
13. Co jest najbardziej generyczne/off-brand w tej ścieżce?
14. Jaki jeden następny krok zrobiłbyś po tej sesji?

## Wynik sesji

Uzupełnić po rozmowie:

- data sesji:
- osoba:
- czas do zrozumienia statusu:
- wybrany work item:
- pokazane materiały review:
- czy Wilku rozumie blokady pełnego UAT:
- czy Service Profile jest czytelny:
- czy public service review actions są czytelne:
- czy private review actions są czytelne:
- czy private policy review actions są czytelne:
- punkty niezrozumienia:
- pytania "skąd to wzięło?":
- miejsca generyczne/off-brand:
- największy brak produktu:
- czy można przejść do pełnego content UAT:
- follow-up Beads:
- Sales Brief gate pokazany w live provenance:

Walidowany format wyniku:

```json
{
  "data_sesji": "YYYY-MM-DD",
  "osoba": "Wilku",
  "czas_do_zrozumienia_statusu": "np. 8 minut",
  "punkty_niezrozumienia": "gdzie Wilku się zgubił, co wymagało tłumaczenia albo co było nieczytelne",
  "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
  "pokazane_materialy_review": [
    "docs/handoffs/2026-07-02-wilq-marketing-content-model.md",
    "docs/handoffs/2026-07-02-co-pokazac-wilkowi.md",
    "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md",
    "docs/handoffs/2026-07-01-wilku-eko-opieka-review.md",
    "docs/handoffs/2026-07-01-wilku-audyt-zgodnosci-review.md",
    "docs/handoffs/2026-07-02-wilku-ekologus-ai-policy-review.md"
  ],
  "pytania_skad_to_wzielo": "co było jasne albo niejasne w evidence IDs/source connectors",
  "miejsca_generyczne_off_brand": "co brzmiało generycznie albo nie jak Ekologus",
  "najwiekszy_brak_produktu": "najważniejszy brak w produkcie/WILQ po sesji",
  "wilku_rozumie_blokady_pelnego_uat": "tak",
  "service_profile_czytelny": "tak",
  "public_service_review_actions_czytelne": "nie",
  "private_review_actions_czytelne": "nie",
  "private_policy_review_actions_czytelne": "nie",
  "mozna_przejsc_do_pelnego_content_uat": "nie",
  "follow_up_beads": [
    "wilq-seo-xyz: doprecyzować publiczne/private review actions przed pełnym UAT"
  ]
}
```

Sprawdzenie wyniku po sesji:

```bash
rtk uv run python scripts/record_goal_005_content_uat_result.py .local-lab/proof/goal-005-content-uat-result-YYYYMMDD.json --format markdown
```

Mocniejsze sprawdzenie z live WILQ API:

```bash
rtk uv run python scripts/record_goal_005_content_uat_result.py .local-lab/proof/goal-005-content-uat-result-YYYYMMDD.json --api-base http://127.0.0.1:8000 --format markdown
```

Ten walidator sprawdza kompletność realnego wyniku sesji i renderuje raport
review. Z `--api-base` dodatkowo sprawdza, czy wybrany work item występuje w
aktualnej kolejce UAT WILQ, zapisuje status kolejki, źródła wybranego itemu,
read-only Service Profile, production-depth readiness, liczbę publicznych i
prywatnych review actions, rozdział private service/policy review, stan private
proposal promotion oraz Sales Brief provenance wybranego itemu. Przy obecnym
live stanie raport zapisze `Sales Brief status: blocked` i blockery `Brakuje
karty usługi; Brakuje karty CTA`. Nie promuje private proposals do source
facts, nie zatwierdza publicznych service cards, nie odblokowuje publikacji ani
nie zamyka Goal 005 automatycznie.

Sprawdzenie domknięcia Goal 005 po wyniku UAT:

```bash
rtk uv run python scripts/goal_005_completion_check.py --uat-result .local-lab/proof/goal-005-content-uat-result-YYYYMMDD.json --api-base http://127.0.0.1:8000 --format markdown
```

Jeżeli wynik UAT nadal wymaga follow-up, completion check ma pozostać
`blocked_missing_goal_005_uat_proof`, ale zachowa w raporcie Sales Brief gate
pokazany Wilkowi. To jest poprawne: widoczny blocker jest dowodem kontroli
jakości, nie dowodem ukończenia Goal 005.

Walidator wymaga też pola `pokazane_materialy_review`. Każda ścieżka musi być
repo-relative, istnieć w `docs/handoffs/` i wskazywać materiał, który realnie
pokazano Wilkowi w sesji. To chroni proof UAT przed pustym stwierdzeniem, że
sesja się odbyła, bez wskazania materiałów review.

Walidator ostrzega, jeżeli przed technicznymi handoffami nie pokazano prostych
materiałów startowych:

- `docs/handoffs/2026-07-02-wilq-marketing-content-model.md`;
- `docs/handoffs/2026-07-02-co-pokazac-wilkowi.md`.

## Kryterium przejścia dalej

Pełny Goal 005 UAT można uznać za wykonany dopiero, gdy Wilku realnie przejdzie
sesję i wypełnimy wynik powyżej. Ten dokument jest przygotowaniem, nie dowodem
ukończonego UAT.
