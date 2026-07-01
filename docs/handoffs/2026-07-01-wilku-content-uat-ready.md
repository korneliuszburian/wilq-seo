# Wilku Content UAT - przygotowanie sesji

Data przygotowania: 2026-07-01

Status: gotowe do pokazania jako sesja review/blokad i traceability, nie jako
ukończony UAT.

Źródło live:

```bash
rtk uv run python .agents/skills/wilq-content-operator/scripts/build_uat_packet.py --api-base http://127.0.0.1:8000 --limit 3 --format markdown
```

## Co sprawdzamy

Cel sesji: sprawdzić, czy Wilku rozumie aktualny stan WILQ bez tłumaczenia
przez developera:

- dlaczego pełny content UAT jest jeszcze zablokowany;
- czy Service Profile jasno pokazuje luki wiedzy i review-required źródła;
- czy prywatne propozycje z `ekologus-ai` są czytelne jako materiał do review,
  a nie jako zatwierdzona wiedza;
- czy przy obecnej kolejce Wilku umie wskazać bezpieczny następny krok;
- czy na pytanie "skąd to wzięło?" widzi evidence IDs i source connectors.

## Aktualny stan WILQ

UAT readiness:

- status: `blocked_for_full_uat`;
- zakres, który można uczciwie pokazać: review/blokady i traceability;
- blokady pełnej sesji: Service Profile nie jest production-depth, prywatne
  propozycje wymagają review Wilka/ownera, kolejka content workflow ma status
  `blocked`;
- liczba gotowych kandydatów w kolejce: 1.

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

## Kandydaci z kolejki

### GA4 tracking gap

- work item: `content_work_item_content_decision_ga4_tracking_gap_block`;
- tryb: `block`;
- dowody:
  `ev_refresh_refresh_google_analytics_4_5ebc4ba1c966`,
  `ev_refresh_refresh_google_analytics_4_33a4b3fda0db`;
- source connector: `google_analytics_4`;
- final canonical: brak;
- pytanie do Wilka: czy to jest zrozumiałe jako problem pomiaru, a nie temat
  do pisania?

### Ahrefs gap

- work item: `content_work_item_content_decision_ahrefs_gap_records_review`;
- tryb: `block`;
- dowody:
  `ev_refresh_refresh_ahrefs_3155c5fa77cf`,
  `ev_refresh_refresh_ahrefs_13a8fb4bd86b`;
- source connector: `ahrefs`;
- final canonical: brak;
- pytanie do Wilka: czy blocker duplikacji/canonical jasno zatrzymuje pisanie?

### Strona główna Ekologus

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
7. Czy `https://www.ekologus.pl/` jako kandydat refresh ma dla Ciebie sens, czy
   lepiej wymusić bardziej konkretny temat, np. BDO?
8. Co jest najbardziej generyczne/off-brand w tej ścieżce?
9. Jaki jeden następny krok zrobiłbyś po tej sesji?

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

## Kryterium przejścia dalej

Pełny Goal 005 UAT można uznać za wykonany dopiero, gdy Wilku realnie przejdzie
sesję i wypełnimy wynik powyżej. Ten dokument jest przygotowaniem, nie dowodem
ukończonego UAT.
