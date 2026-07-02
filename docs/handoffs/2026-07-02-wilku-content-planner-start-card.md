# Content Planner: co pokazać Wilkowi

Data: 2026-07-02

## Krótko

WILQ Content Planner jest już użyteczny jako kolejka decyzji treści:
odświeżyć, scalić, potraktować lukę Ahrefs jako materiał do sprawdzenia albo
zablokować temat jako problem pomiaru, nie contentu.

Najważniejsze: WILQ nie zaczyna od pisania. Najpierw sprawdza GSC, WordPress,
Ahrefs, GA4 i spis treści, żeby nie robić duplikatu ani nie obiecywać wyniku
bez dowodów.

## Aktualny stan

- Endpoint: `/api/content/diagnostics`.
- `live_data_available=true`.
- Kolejka decyzji: 3 pozycje.
- Dowody: 16 identyfikatorów dowodów.
- Akcje do sprawdzenia: 5.
- Wymagane źródła są skonfigurowane: GSC, GA4, Ahrefs, WordPress ekologus.pl i
  WordPress sklep.ekologus.pl.
- `wilq-content-strategist` smoke przeszedł i potwierdził osadzone
  `content_diagnostics` w context-packu.

## Najważniejsze decyzje

1. Ahrefs: zweryfikować luki SEO przed planem treści.
   Nie publikować na podstawie samej luki konkurencji; połączyć z GSC i
   WordPress.
2. SEO: odświeżyć albo scalić istniejący adres dla zapytań wokół `ekologus`.
   WordPress potwierdza istniejącą stronę, więc to nie jest nowy artykuł.
3. GA4: zablokować braki pomiaru jako zadania contentowe.
   `(not set)` i tracking gap to problem pomiaru, nie powód do rewrite’u.

## Dowody i akcje

- Źródła: `ahrefs`, `google_search_console`, `wordpress_ekologus`,
  `wordpress_sklep`, `google_analytics_4`.
- Główne dowody:
  - `ev_refresh_refresh_ahrefs_5eee21244cff`
  - `ev_refresh_refresh_ahrefs_3155c5fa77cf`
  - `ev_refresh_refresh_google_search_console_9b25d4143bea`
  - `ev_refresh_refresh_wordpress_ekologus_691cbe6ab27d`
  - `ev_refresh_refresh_google_analytics_4_5ebc4ba1c966`
  - `ev_refresh_refresh_google_analytics_4_33a4b3fda0db`
- Główne akcje:
  - `act_prepare_content_refresh_queue`
  - `act_prepare_wordpress_draft_handoff`
  - `act_review_ga4_tracking_quality`

## Czego nie wolno obiecywać

- Nie obiecywać wzrostu pozycji, ruchu, leadów, konwersji ani przychodu.
- Nie twierdzić, że temat jest nowy bez kontroli spisu treści.
- Nie twierdzić braku duplikatów bez WordPress/canonical/social-history check.
- Nie publikować ani nie zapisywać WordPress bez akcji, podglądu, zgody i
  audytu.

## Ocena użyteczności

- Użyteczność jako kolejka decyzji contentowych: 8/10.
- Użyteczność jako generator gotowego tekstu produkcyjnego: 5.5/10, bo nadal
  brakuje pełnego Claim Ledger i zatwierdzonej głębokiej wiedzy usługowej.
- Blokowanie fałszywych claimów: 8.5/10.
- Pierwszy ekran po zmianie: 7.5/10, bo pokazuje `Treści: co dziś zrobić`,
  `Kolejność pracy` i `Czego nie obiecywać` przed technicznym przeglądem.

## Co jeszcze dopracować

- Podpiąć pełny Claim Ledger jako bramkę draftu, nie tylko listę blokad.
- Dodać historyczne posty LinkedIn/Facebook jako dedupe metadata, zanim WILQ
  będzie mówił, że temat jest nowy albo bezpieczny do repurpose.
- Lepiej pokazać relację: luka Ahrefs -> popyt GSC -> istniejąca treść
  WordPress -> decyzja refresh/merge/create/block.
