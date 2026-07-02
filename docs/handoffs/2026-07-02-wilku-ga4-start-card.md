# GA4: co pokazać Wilkowi

Data: 2026-07-02

## Krótko

WILQ GA4 jest dobrym materiałem do rozmowy o jakości ruchu, ale najpierw trzeba
oddzielić problem pomiaru od problemu marketingowego.

Aktualna kolejność:

1. Najpierw wyjaśnić dwa wiersze `(not set)`: brak strony wejścia albo źródła
   w GA4 to luka pomiaru/atrybucji, nie dowód że kampania lub SEO są słabe.
2. Potem sprawdzić dwa gotowe wiersze `google / cpc`: strona główna i artykuł
   o warunkach zabudowy jako kandydaci do kontroli dopasowania reklamy,
   strony wejścia i intencji.
3. Nie mówić o ROAS, przychodzie, opłacalności, spadku konwersji ani naprawie
   pomiaru bez osobnych dowodów kosztu, atrybucji, konwersji i wdrożenia.

## Dowody

- Źródła: `google_analytics_4`, `wordpress_ekologus`.
- GA4 jest skonfigurowane i ma świeży odczyt w progu 48h.
- WILQ pokazał 4 decyzje GA4: 2 problemy pomiaru i 2 kontrole jakości ruchu.
- Główne dowody:
  - `ev_refresh_refresh_google_analytics_4_5ebc4ba1c966`
  - `ev_refresh_refresh_google_analytics_4_33a4b3fda0db`
  - `ev_refresh_refresh_wordpress_ekologus_691cbe6ab27d`
  - `ev_connector_google_analytics_4_status`
- Akcja do sprawdzenia: `act_review_ga4_tracking_quality`.

## Ocena użyteczności

- Rozdzielenie problemu pomiaru od marketingu: 8/10.
- Użyteczność dla marketera: 7-7.5/10.
- Blokowanie fałszywych claimów: 9/10.

Po zmianie dashboardu pierwszy ekran ma blok `Najpierw pomiar`, więc Wilku nie
musi rozwijać technicznego przeglądu, żeby zobaczyć dlaczego `(not set)` blokuje
ocenę kampanii.

## Co jeszcze dopracować

- Uprościć język panelu akcji, bo ActionObject nadal brzmi technicznie.
- Doprecyzować copy przy gotowości konwersji, żeby “dane są dostępne” nie
  brzmiało jak “można oceniać opłacalność”.
