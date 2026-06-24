# Ekologus Marketer UAT Script

Cel: sprawdzić, czy WILQ realnie pomaga marketerowi wybrać następne działanie
bez tłumaczenia przez developera. To nie jest test produkcyjnego apply, Ads
optimizera, feed repair ani publikacji WordPress.

Limit czasu: 15 minut.

## Przygotowanie

- Otwórz dashboard: `http://127.0.0.1:5173/command-center`.
- Nie tłumacz wcześniej znaczenia statusów. Obserwuj, gdzie marketer sam wie,
  co kliknąć, a gdzie pyta o wyjaśnienie.
- Jeżeli ekran pokazuje blocker, oceniaj czy blocker jest zrozumiały, nie czy
  narzędzie omija blocker.

## Ścieżka

1. Command Center
   - Marketer ma wskazać jedną decyzję dnia.
   - Pass: umie powiedzieć, co sprawdzić dalej i dlaczego.
   - Fail: widzi tylko statusy techniczne albo nie wie, który moduł otworzyć.

2. Merchant
   - Marketer ma wskazać jeden problem feedu albo blocker.
   - Pass: rozumie, że zgłoszenia problemów nie są automatycznie unikalnymi SKU
     i że feed write/approval recovery nie są obiecane.
   - Fail: interpretuje liczby jako gotową listę produktów do automatycznej
     naprawy.

3. Content Planner
   - Marketer ma wybrać jeden temat refresh/merge, np. BDO albo Zielony Ład.
   - Pass: widzi source evidence, target context, inventory gate, canonical,
     duplicate gate, H1/H2/FAQ/CTA direction, missing evidence i forbidden
     claims.
   - Fail: uważa, że WILQ już wygenerował publish-ready artykuł albo że
     `ekologus.dev.proudsite.pl` jest źródłem historycznej skuteczności.

4. Ads Doctor
   - Marketer ma wskazać jedną kolejkę review: campaign, recommendations,
     search terms, custom segments albo negative keywords.
   - Pass: rozumie, że CPA/ROAS/wasted budget/budget scaling/apply są
     zablokowane bez targetów, review i audit contract.
   - Fail: oczekuje automatycznej optymalizacji albo gotowego werdyktu
     opłacalności.

5. GA4
   - Marketer ma wskazać jeden problem pomiaru.
   - Pass: rozumie, że `(not set)` to problem tracking/attribution, nie dowód
     złej kampanii albo złego landingu.
   - Fail: interpretuje tracking gap jako rekomendację contentową lub Adsową.

## Pytania końcowe

Zadaj marketerowi dokładnie te pytania:

1. Czy wiesz, co zrobić jako następny krok?
2. Który ekran dał Ci największy realny zysk?
3. Gdzie musiałeś zgadywać znaczenie statusu albo pola?
4. Czy Content Planner oszczędza Ci czas przy planowaniu treści na nową stronę?
5. Ile czasu realnie oszczędza ta ścieżka: 0, 15, 30, 60+ minut?

## Wynik

Uzupełnij po sesji:

- Data:
- Osoba:
- Pass/fail Command Center:
- Pass/fail Merchant:
- Pass/fail Content Planner:
- Pass/fail Ads Doctor:
- Pass/fail GA4:
- Największy realny boost:
- Największe niezrozumienie:
- Nowe zadania:
- Czy demo jest gotowe do pokazania bez developera: tak/nie

## Kryterium demo

Demo jest solidne dopiero wtedy, gdy marketer potrafi sam:

- wybrać jedną decyzję dnia,
- wskazać jeden brief refresh/merge,
- nazwać jeden blocker Merchant/Ads/GA4,
- i powiedzieć, jaki jest następny bezpieczny krok.

Jeśli to się nie dzieje, problemem nie jest brak kolejnego modułu, tylko UX,
copy albo priorytetyzacja istniejącej ścieżki.
