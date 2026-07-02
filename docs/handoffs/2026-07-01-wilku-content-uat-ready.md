# Wilku Content UAT - przygotowanie sesji

Data przygotowania: 2026-07-01
Ostatnia aktualizacja: 2026-07-02 00:50 CEST

Status: gotowe do pokazania jako sesja review/blokad i traceability, nie jako
ukończony UAT.

Aktualizacja po live refreshu: 2026-07-01 22:39 UTC. WILQ odświeżył stale
źródła Merchant/Ahrefs/WordPress sklep, więc ten handoff nie zakłada już, że
content/merchant są zablokowane przez nieświeże dane. Pełny UAT nadal jest
zablokowany przez brak production-depth Service Profile i review prywatnych
propozycji.

Aktualizacja po hardeningu Claim Ledger: claimy oznaczone jako
`allowed_with_evidence` muszą mieć teraz nie tylko `evidence_ids`, ale też
`source_connectors`. Brak źródła danych blokuje gotowość szkicu przez
`missing_source_connector`. Dzięki temu pytanie "skąd to wzięło?" nie kończy
się samym technicznym ID dowodu, tylko prowadzi do konkretnego źródła danych.

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
- czy prywatne propozycje z `ekologus-ai` są czytelne jako materiał do review,
  a nie jako zatwierdzona wiedza;
- czy przy obecnej kolejce Wilku umie wskazać bezpieczny następny krok;
- czy na pytanie "skąd to wzięło?" widzi evidence IDs i source connectors;
- czy rozumie, że claim z dowodem bez źródła danych jest teraz blokowany, a nie
  przepychany do szkicu.

## Aktualny stan WILQ

UAT readiness:

- status: `blocked_for_full_uat`;
- zakres, który można uczciwie pokazać: review/blokady i traceability;
- blokady pełnej sesji: Service Profile nie jest production-depth, prywatne
  propozycje wymagają review Wilka/ownera, kolejka content workflow ma status
  `blocked`;
- liczba gotowych kandydatów w kolejce: 1.
- kolejka: `candidate_count=3`, `actionable_candidate_count=1`,
  `queue_status=blocked`.
- świeże proof IDs po odświeżeniu źródeł:
  `refresh_google_merchant_center_a04a45a6e6fd`,
  `refresh_ahrefs_5eee21244cff`,
  `refresh_wordpress_sklep_c1db9b8fa677`.

Service Profile:

- endpoint: `GET /api/content/service-profile`;
- tryb: read-only;
- production-depth: false;
- status: źródła są, wymagają review;
- następny krok: przejrzeć karty review-required i luki usługowe z Wilkiem
  przed użyciem ich jako production-depth.

Luki do omówienia:

- `gap_service_operat_wodnoprawny`: brak bezpośredniej karty usługi dla operatu
  wodnoprawnego;
- `gap_no_approved_current_cards`: brak zatwierdzonych production-depth kart
  usług.

Private review actions:

- `service_profile_review_private_proposal_ekologus_ai_eko_opieka_2026_07_01`:
  sprawdzić prywatną propozycję Eko-Opieka / Eko Kalendarz;
- `service_profile_review_private_proposal_ekologus_ai_audyt_zgodnosci_2026_07_01`:
  sprawdzić prywatną propozycję Audyt zgodności środowiskowej.

Obie akcje mają ten sam warunek bezpieczeństwa: to nie promuje private proposal
do source fact ani knowledge card.

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

### SEO: odśwież lub scal "ekologus" (25 zapytań)

- work item: `content_work_item_content_decision_https___www_ekologus_pl`;
- tryb: `refresh`;
- status: gotowe do planu;
- dowody:
  `ev_refresh_refresh_google_search_console_b545c32e13f1`,
  `ev_refresh_refresh_wordpress_ekologus_691cbe6ab27d`;
- source connectors: `google_search_console`, `wordpress_ekologus`;
- final canonical: `https://www.ekologus.pl/`;
- pytanie do Wilka: czy przy takim temacie WILQ powinien przygotować plan
  odświeżenia strony głównej, czy to jest zbyt szeroki kandydat na pierwszy
  content UAT?

## Pytania do Wilka

Zadaj dokładnie te pytania i wpisz odpowiedzi w sekcji wyników:

1. Czy rozumiesz, dlaczego pełny content UAT jest teraz zablokowany?
2. Który blocker jest najbardziej sensowny, a który brzmi technicznie?
3. Czy Service Profile mówi Ci, czego brakuje w wiedzy Ekologus?
4. Czy private review actions dla Eko-Opieki i Audytu zgodności są czytelne?
5. Czy widzisz, że te prywatne propozycje nie są jeszcze zatwierdzoną wiedzą?
6. Gdy pytasz "skąd to wzięło?", czy evidence IDs i source connectors są
   wystarczające?
7. Czy blokada `missing_source_connector` jest zrozumiała po ludzku jako "brak
   źródła danych dla twierdzenia"?
8. Czy `https://www.ekologus.pl/` jako kandydat refresh ma dla Ciebie sens, czy
   lepiej wymusić bardziej konkretny temat, np. BDO?
9. Co jest najbardziej generyczne/off-brand w tej ścieżce?
10. Jaki jeden następny krok zrobiłbyś po tej sesji?

## Wynik sesji

Uzupełnić po rozmowie:

- data sesji:
- osoba:
- czas do zrozumienia statusu:
- wybrany work item:
- czy Wilku rozumie blokady pełnego UAT:
- czy Service Profile jest czytelny:
- czy private review actions są czytelne:
- pytania "skąd to wzięło?":
- miejsca generyczne/off-brand:
- największy brak produktu:
- czy można przejść do pełnego content UAT:
- follow-up Beads:

Walidowany format wyniku:

```json
{
  "data_sesji": "YYYY-MM-DD",
  "osoba": "Wilku",
  "czas_do_zrozumienia_statusu": "np. 8 minut",
  "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
  "pytania_skad_to_wzielo": "co było jasne albo niejasne w evidence IDs/source connectors",
  "miejsca_generyczne_off_brand": "co brzmiało generycznie albo nie jak Ekologus",
  "najwiekszy_brak_produktu": "najważniejszy brak w produkcie/WILQ po sesji",
  "wilku_rozumie_blokady_pelnego_uat": "tak",
  "service_profile_czytelny": "tak",
  "private_review_actions_czytelne": "nie",
  "mozna_przejsc_do_pelnego_content_uat": "nie",
  "follow_up_beads": [
    "wilq-seo-xyz: doprecyzować private review actions przed pełnym UAT"
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
read-only Service Profile, production-depth readiness i stan private proposal
promotion. Nie promuje private proposals do source facts, nie zatwierdza
knowledge cards, nie odblokowuje publikacji ani nie zamyka Goal 005
automatycznie.

## Kryterium przejścia dalej

Pełny Goal 005 UAT można uznać za wykonany dopiero, gdy Wilku realnie przejdzie
sesję i wypełnimy wynik powyżej. Ten dokument jest przygotowaniem, nie dowodem
ukończonego UAT.
