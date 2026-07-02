# Merchant: co pokazać Wilkowi

Data: 2026-07-02

## Krótko

WILQ Merchant jest już użyteczny jako kolejka przeglądu pliku produktowego.
Nie jest jeszcze narzędziem do twierdzeń o przychodzie, ROAS produktu,
odzyskanym zatwierdzeniu ani automatycznej naprawie feedu.

Aktualna kolejność:

1. Najpierw sprawdzić powiązanie próbek Merchant ze statusem produktów w Google
   Ads albo największy problem atrybutu w kolejce Merchant.
2. Potem przygotować podgląd zmian przez `act_review_merchant_feed_issues`.
3. Nie zapisywać zmian do pliku produktowego, nie obiecywać ponownego
   zatwierdzenia i nie oceniać wpływu ceny bez brakujących kontraktów.

## Aktualny stan

- Merchant Center jest skonfigurowany.
- Ostatni odczyt: `refresh_google_merchant_center_a04a45a6e6fd`.
- Dane są świeże: około 12.8h, próg 48h.
- `metrics_persisted=true`.
- WILQ widzi 10476 produktów i 15 problemów/zgłoszeń problemów w bieżącym
  odczycie.
- Kolejka decyzji ma 6 pozycji.
- Akcja do sprawdzenia: `act_review_merchant_feed_issues`, walidacja `valid`.

## Dowody

- Źródła: `google_merchant_center`, częściowo `google_ads` dla powiązania
  próbek produktów ze statusem Ads.
- Główne dowody:
  - `ev_refresh_refresh_google_merchant_center_a04a45a6e6fd`
  - `ev_connector_google_merchant_center_status`
  - `ev_refresh_refresh_google_ads_be7011a4a261`
  - `ev_refresh_refresh_google_ads_8790a6ba1a50`

## Najważniejsze decyzje

- Sprawdzić powiązanie 2 próbek Merchant ze statusem produktów w Google Ads:
  status, dostępność, cena, powiązany problem Merchant i podgląd uzupełnienia
  pliku produktowego.
- Sprawdzić problem `miara ceny jednostkowej`: 415 największych zgłoszeń w
  raporcie, 1245 zgłoszeń razem w kontekstach raportowania.
- Sprawdzić problem `dostępność`: 10 największych zgłoszeń w raporcie, 30
  zgłoszeń razem.
- Sprawdzić małe problemy: link zdjęcia i certyfikacja.
- `wpływ ceny` pozostaje zablokowany.

## Czego nie wolno twierdzić

- Nie twierdzić, że znamy liczbę unikalnych produktów/SKU z sumy raportów.
- Nie twierdzić ponownego zatwierdzenia produktu.
- Nie twierdzić odzyskanego przychodu, ROAS produktu, efektu naprawy produktu
  ani skalowania w Shopping/PMax.
- Nie twierdzić wpływu ceny bez historii zmiany ceny i okna skuteczności.
- Nie twierdzić zapisu do pliku produktowego bez audytu i potwierdzenia.

## Ocena użyteczności

- Użyteczność jako kolejka review pliku produktowego: 8/10.
- Użyteczność do decyzji performance/product revenue: 5.5/10, bo brakuje pełnego
  joinu Ads/GA4 dla skuteczności produktu.
- Blokowanie fałszywych claimów: 9/10.
- Pierwszy ekran po zmianie: 7.5/10, bo pokazuje `Merchant: co dziś zrobić`,
  kolejność pracy i `Czego nie obiecywać` bez rozwijania pełnego przeglądu.

## Co jeszcze dopracować

- Pokazać najważniejszą decyzję i największy problem atrybutu obok siebie, a nie
  tylko jeden primary decision.
- Dodać pełniejszy join skuteczności produktu Ads/GA4, zanim WILQ będzie
  odpowiadał na pytania o ROAS/przychód produktu.
