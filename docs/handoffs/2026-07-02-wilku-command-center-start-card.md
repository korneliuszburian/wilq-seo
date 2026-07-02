# Centrum pracy: co pokazać Wilkowi

Data: 2026-07-02

## Krótko

To jest obecnie najbliższy ekran do BDOS-owego “porannego sprawdzenia”.
WILQ mówi, od czego zacząć dzień, które decyzje są gotowe, które są
zablokowane i do jakiego widoku przejść bez ręcznego skakania po narzędziach.

Dzisiejszy pierwszy krok z API:

> Najpierw otwórz widok Merchant i przejrzyj kolejkę problemów pliku produktowego.

## Aktualny plan dnia z WILQ

1. Merchant: przejrzeć kolejkę problemów pliku produktowego.
2. Treści: przejrzeć kolejkę SEO z GSC i WordPress.
3. GA4: rozdzielić problem pomiaru od jakości ruchu.
4. Google Ads: przejrzeć odczyt Ads bez zapisu zmian.

## Aktualny stan

- Endpoint: `/api/dashboard/command-center`.
- `primary_next_step`: Merchant jako pierwszy krok.
- `daily_decisions`: 4.
- `blocker_count`: 2.
- `tactical_item_count`: 24.
- Connector summary: 12 źródeł, 9 skonfigurowanych, 2 z brakującymi
  credentials.
- Social nie jest promowany w planie dnia.

## Dowody i akcje

- Merchant:
  - dowody: `ev_refresh_refresh_google_merchant_center_a04a45a6e6fd`,
    `ev_connector_google_merchant_center_status`
  - akcja: `act_review_merchant_feed_issues`
- Treści:
  - dowody: `ev_refresh_refresh_ahrefs_5eee21244cff`,
    `ev_refresh_refresh_google_search_console_9b25d4143bea`,
    `ev_refresh_refresh_wordpress_ekologus_691cbe6ab27d`
  - akcje: `act_prepare_content_refresh_queue`,
    `act_prepare_wordpress_draft_handoff`
- GA4:
  - dowody: `ev_refresh_refresh_google_analytics_4_5ebc4ba1c966`,
    `ev_refresh_refresh_google_analytics_4_33a4b3fda0db`,
    `ev_refresh_refresh_wordpress_ekologus_691cbe6ab27d`
  - akcja: `act_review_ga4_tracking_quality`
- Ads:
  - dowody: `ev_connector_google_ads_status`,
    `ev_refresh_refresh_google_ads_be7011a4a261`
  - akcje: `act_prepare_ads_campaign_review_queue`,
    `act_prepare_google_ads_recommendation_review_queue`,
    `act_prepare_custom_segments_from_search_terms`,
    `act_prepare_negative_keyword_review_queue`

## Czego nie wolno obiecywać

- Merchant: ponowne zatwierdzenie produktu, odzyskany przychód, automatyczna
  zmiana pliku produktowego.
- Treści: jakość leadów, wzrost konwersji, wpływ na przychód.
- GA4: ROAS, przychód, spadek konwersji, naprawiony pomiar.
- Ads: koszt pozyskania celu, ROAS, zmarnowany budżet, zapis rekomendacji,
  zmiana budżetu, opłacalność.

## Ocena użyteczności

- Poranny “co robić dziś?”: 8.5/10.
- Dowody i bezpieczeństwo claimów: 8.5/10.
- Użyteczność jako pełny BDOS daily command: 7.5/10, bo nadal trzeba wejść w
  poszczególne widoki po szczegóły akcji.

Po zmianie dashboardu pierwszy ekran pokazuje `Plan dnia w kolejności` i
`Blokady dnia` przed dużymi kartami decyzji.

## Co jeszcze dopracować

- Dodać bardziej skrócony “1 klik: uruchom właściwy skill” bez kopiowania
  polecenia ręcznie.
- Dodać na topie krótkie “dlaczego Merchant jest pierwszy” z API, nie jako
  frontendową interpretację.
