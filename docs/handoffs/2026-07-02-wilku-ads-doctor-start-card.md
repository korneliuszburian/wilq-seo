# Ads Doctor: karta startowa dla Wilka

Status: materiał do review Ads, nie zgoda na zapis zmian.

Data testu: 2026-07-02

## Decyzja na dziś

Wilku, WILQ mówi: **zacznij od przeglądu kampanii Ads, nie od zmian w koncie**.

Dzisiejsza kolejność pracy:

1. Sprawdź kolejkę 18 kampanii: największy ruch, koszt i sygnał review.
2. Potem przejrzyj 50 wyszukiwanych haseł i 4 kandydatów do wykluczeń, ale
   tylko jako review.
3. Dopiero później sprawdzaj rekomendacje Google Ads, historię zmian i segmenty.

## Co WILQ widzi

Live WILQ API na 2026-07-02:

- `live_data_available=true`
- 18 kampanii
- 81 kliknięć
- 2248 wyświetleń
- koszt: 151 PLN
- 0 konwersji w bieżącym odczycie
- 50 wierszy wyszukiwanych haseł
- 200 wierszy safety z 90 dni
- 3 aktywne rekomendacje Google Ads
- 41 zdarzeń historii zmian

Dowody:

- `ev_connector_google_ads_status`
- `ev_refresh_refresh_google_ads_be7011a4a261`

## Czego WILQ nie pozwala twierdzić

Nie mówimy dziś:

- "to przepalony budżet";
- "to się opłaca / nie opłaca";
- "mamy ROAS/CPA verdict";
- "trzeba skalować budżet";
- "dodać te wykluczenia";
- "rekomendacje Google Ads można zaakceptować";
- "zmiany poprawiły wynik".

Powód: brakuje m.in. `target_roas_or_cpa`, `human_strategy_review`,
`human_intent_review`, preview zmian i okien przed/po zmianie.

## Akcje do sprawdzenia

WILQ ma akcje review-only:

- `act_prepare_ads_campaign_review_queue`
- `act_prepare_google_ads_recommendation_review_queue`
- `act_review_ads_change_history_impact`
- `act_prepare_negative_keyword_review_queue`
- `act_review_ads_search_term_ngrams`
- `act_prepare_custom_segments_from_search_terms`

To są akcje do walidacji i podglądu. Nie oznaczają zapisu zmian w Google Ads.

## Ocena użyteczności

Testy wykonane:

- `wilq-ads-doctor` smoke: przeszedł;
- `POST /api/codex/context-pack` dla `wilq-ads-doctor`: zgodny z Ads
  diagnostics, ale skompaktowany;
- pełne `GET /api/ads/diagnostics`: użyte jako źródło prawdy dla kolejki;
- dwie niezależne oceny reviewerów: Ads specialist i marketer/operator.

Wyniki:

- ogólna użyteczność BDOS-style: **7/10**;
- materiał review dla marketera: **7.5/10**;
- gotowość do bezpiecznych zmian: **5.5/10**;
- blokowanie fałszywych claimów: **8.5/10**;
- first-screen clarity dla Wilka: **6.5/10 przed zmianą UI**, oczekiwane ok.
  **8/10** po dodaniu karty "Ads Doctor: co dziś zrobić".

## Najważniejszy tuning

Pierwszy ekran `/ads-doctor` powinien zaczynać od listy:

1. co sprawdzić najpierw;
2. co jest tylko review;
3. czego nie wolno twierdzić;
4. jakie dane blokują decyzje biznesowe.

Ten tuning został wprowadzony w dashboardzie jako karta
`Ads Doctor: co dziś zrobić` z sekcją `Kolejność pracy`.
