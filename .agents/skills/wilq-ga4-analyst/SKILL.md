---
name: wilq-ga4-analyst
description: Analizuje zachowanie GA4 dla Ekologus z dowodami z WILQ API. Użyj, gdy marketer pyta "które strony wejścia działają słabo?", "czy ruch z kampanii ma sens?", "czemu użytkownicy nie angażują się?", "czy pomiar jest zepsuty?", "porównaj źródła ruchu", albo pyta o zaangażowanie, sesje, jakość kampanii/źródła, diagnostykę konwersji lub braki pomiaru. Musi cytować GA4 identyfikatory dowodów i nie wolno zmyślać wartości GA4.
---

# WILQ Analityka GA4

## Zasada skilla

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Kiedy używać

<triggers>

- "Które strony wejścia w Ekologus są najsłabsze?"
- "Sprawdź jakość ruchu z kampanii i źródeł."
- "Czy GA4 pokazuje problem marketingowy czy problem pomiaru?"
- "Znajdź braki pomiaru, zanim ocenimy kampanie."

</triggers>

## Workflow operatora

<workflow>

1. Wywołaj `GET /api/ga4/diagnostics` przed podsumowaniem zachowania GA4, jakości stron wejścia, gotowości konwersji lub blokad pomiaru.
2. Użyj `ga4_diagnostics.decision_queue` jako głównej kolejki decyzji i zachowaj etykiety typu, statusu i następnego kroku zwrócone przez API. Techniczne wartości enumów zostaw wyłącznie jako ślad techniczny; nie klasyfikuj GA4 itemów samodzielnie poza danymi API.
3. Pobierz `POST /api/codex/context-pack` tylko gdy wąski endpoint nie wystarcza albo potrzebujesz kontekstu wielu powierzchni. Nie rób z tego obowiązkowego kroku.
4. Endpointów refresh źródeł danych używaj tylko do jawnych odczytów danych i tylko gdy źródło danych jest skonfigurowane.
5. Jeśli użytkownik prosi o zapis albo podgląd zmiany, użyj `POST /api/actions/{action_id}/validate`; w review-only odpowiedzi wystarczy wskazać action_id i bezpieczny następny krok.
6. W podstawowej odpowiedzi używaj polskich podsumowań dowodów i źródeł danych. Techniczne identyfikatory źródeł danych, dowodów, szans i akcji dodawaj tylko jako ślad techniczny, gdy API je udostępnia.

</workflow>

## API

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `POST /api/codex/context-pack`
- `GET /api/marketing/brief`
- `GET /api/ga4/diagnostics`
- `GET /api/marketing/tactical-queue`
- `GET /api/connectors`
- `GET /api/connectors/{connector}/status`
- `GET /api/connectors/{connector}/refresh-runs`
- `GET /api/connectors/refresh-runs`
- `GET /api/evidence`
- `GET /api/opportunities`
- `GET /api/actions`
- `GET /api/actions/{action_id}`
- `POST /api/actions/{action_id}/validate`
- `POST /api/connectors/{connector}/refresh` z `mode=vendor_read` tylko wtedy, gdy źródło danych jest skonfigurowane i zadanie jawnie wymaga świeżego odczytu danych.

</allowed_endpoints>

## Dowody

<evidence_requirements>

Wymagane powierzchnie źródeł danych dla tego skilla:

- `google_analytics_4`

Każda rekomendacja musi zawierać identyfikatory źródeł danych i identyfikatory dowodów z WILQ API. Jeśli dowody są zagregowane, stare, niepełne albo zablokowane dostępem do źródła danych, powiedz to wprost.

</evidence_requirements>

## Odpowiedź

<output>

Odpowiedź ma być krótka i użyteczna dla operatora: status, dowody, diagnoza, akcje do sprawdzenia w WILQ, blokady i następne bezpieczne kroki.

Widocznie rozdzielaj trzy rzeczy:

- `Pomiar do naprawy`: wiersze z `(not set)` traktuj jako brak przypisania strony wejścia, źródła albo kampanii. Nie oceniaj po nich kampanii, SEO ani strony.
- `Ruch do oceny`: wiersze z czytelną stroną wejścia i źródłem ruchu można sprawdzać pod kątem dopasowania intencji do landing page.
- `Czego nie wolno twierdzić`: ROI, przychód, spadek konwersji, współczynnik konwersji, zwrot z reklam, naprawiony pomiar albo zapis w GA4 bez osobnych dowodów.

Nie rób z `(not set)` dowodu słabej kampanii. Tłumacz to normalnie: "GA4 nie podało strony wejścia albo źródła, więc to najpierw sprawdzamy jako pomiar". Surowe typy decyzji, endpointy i identyfikatory trzymaj w śladzie technicznym.

Język: wszystkie odpowiedzi dla operatora pisz po polsku z polskimi znakami. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans, identyfikatory akcji, ścieżki endpointów i wartości enumów zostaw bez zmian.

</output>

## Bezpieczeństwo

<safety_rules>

<!-- no-invented-metrics guardrail: do not invent metrics. -->
<!-- Polish language rule: operator-facing responses must be in Polish with Polish diacritics. -->

- Nie wymyślaj metryk, rankingów, liczby produktów, stanu kampanii, spisu treści, dostępów social ani ustaleń Localo.
- Nie drukuj sekretów, ścieżek credentiali, wartości tokenów ani surowych vendor response bodies.
- Nie wywołuj endpointów zapisu zmian, chyba że WILQ API wystawia akcję, sprawdzenie w WILQ przechodzi i użytkownik jawnie prosi o zapis zmian.
- Nie omijaj sprawdzenia w WILQ, identyfikatorów dowodów ani wymagań audytu.
</safety_rules>
