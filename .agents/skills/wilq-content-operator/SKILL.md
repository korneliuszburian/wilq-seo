---
name: wilq-content-operator
description: Prowadzi operacyjny workflow tworzenia treści Ekologus przez WILQ API. Użyj, gdy marketer pyta o kolejkę tematów, wybór propozycji, enrichment, wariant szkicu, quality review, rewizję, human review, WordPress draft-only albo interpretację pomiaru. Skill musi używać WILQ API i nie wolno mu zmyślać metryk.
---

# WILQ Content Operator

## Kontrakt skilla

<operating_rule>

Używaj tego skilla jako operatora procesu WILQ Content Operations, nie jako autora tekstu ani prompt-packa. WILQ API jest mózgiem produktu: wybiera propozycje, liczy bramki, buduje enrichment, brief, rejestr twierdzeń, draft package, warianty, quality review, rewizję, human review, WordPress draft-only i pomiar. Codex może prowadzić workflow i wyjaśniać wynik, ale nie może pisać produkcyjnej treści poza kontraktem WILQ API.

</operating_rule>

## Kiedy używać

<triggers>

- "Przeprowadź mnie przez tworzenie treści w WILQ."
- "Wybierz temat z kolejki treści i pokaż, co dalej."
- "Wygeneruj szkic przez WILQ, ale bez publikacji."
- "Sprawdź jakość szkicu, twierdzenia i blokady przed WordPressem."
- "Przygotuj WordPress draft-only / podgląd zmian i measurement window."
- "Zinterpretuj wynik pomiaru treści, jeśli okno pomiarowe jest gotowe."

</triggers>

## Kontrakt workflow

<workflow>

1. Przeczytaj `references/output-contract.md` przed odpowiedzią dla operatora.
2. Uruchom `uv run python .agents/skills/wilq-content-operator/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000` przy sprawdzaniu ścieżki skill/API.
3. Uruchom `uv run python .agents/skills/wilq-content-operator/scripts/build_uat_packet.py --api-base http://127.0.0.1:8000 --limit 5` przy przygotowaniu krótkiego UAT packetu dla Wilka.
4. Wywołaj `GET /api/health`, a przy awarii zwróć blokadę zamiast planu.
5. Wywołaj `GET /api/content/work-items/queue` i użyj kolejki jako kanonicznego wejścia. Nie buduj własnej listy tematów z promptu.
6. Pobierz `GET /api/content/service-profile`, gdy sesja dotyczy UAT, source trace, knowledge-depth albo prywatnych propozycji.
7. Wybierz `work_item_id` z kolejki albo wyjaśnij, że praca jest zablokowana. Nie odblokowuj propozycji, jeśli API zwraca blocker.
8. Pobierz `GET /api/content/work-items/{work_item_id}/snapshot`, `GET /api/content/work-items/{work_item_id}/enrichment` i `GET /api/content/knowledge-cards`, jeśli workflow dotyczy pisania, rewizji albo handoffu.
9. Pobierz `GET /api/marketing/brief` jako skondensowany marketingowy kontekst route/workflow, nie jako zamiennik queue/snapshot.
10. Dla generowania szkicu używaj tylko ścieżki WILQ API: brief sprzedażowy, rejestr twierdzeń, draft package, structured generation contract, runtime, preview, quality review, revision plan, revision apply i human review. Nie wywołuj OpenAI bezpośrednio.
11. WordPress obsługuj tylko przez WILQ API i tylko jako draft-only albo podgląd zmian. Nie wywołuj WordPress bezpośrednio i nie próbuj publikować.
12. Measurement outcome interpretuj wyłącznie przez WILQ API. Jeśli okno pomiarowe nie jest gotowe, powiedz, że sukces albo porażka są zablokowane.

</workflow>

## API Contract

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `POST /api/codex/context-pack`
- `GET /api/marketing/brief`
- `GET /api/content/service-profile`
- `GET /api/content/work-items/queue`
- `GET /api/content/work-items/snapshot`
- `GET /api/content/work-items/{work_item_id}/snapshot`
- `GET /api/content/work-items/{work_item_id}/enrichment`
- `GET /api/content/knowledge-cards`
- `POST /api/content/work-items/preflight`
- `POST /api/content/work-items/sales-brief`
- `POST /api/content/work-items/draft-package`
- `POST /api/content/work-items/structured-draft-generation`
- `POST /api/content/work-items/structured-draft-runtime`
- `POST /api/content/work-items/structured-draft-preview`
- `POST /api/content/work-items/{work_item_id}/structured-draft-preview`
- `POST /api/content/work-items/draft-variants`
- `POST /api/content/work-items/quality-review`
- `POST /api/content/work-items/{work_item_id}/quality-review`
- `POST /api/content/work-items/revision-plan`
- `POST /api/content/work-items/{work_item_id}/revision-plan`
- `POST /api/content/work-items/revision-apply`
- `POST /api/content/work-items/{work_item_id}/revision-apply`
- `POST /api/content/work-items/human-review`
- `POST /api/content/work-items/{work_item_id}/human-review`
- `POST /api/content/work-items/{work_item_id}/audit`
- `POST /api/content/work-items/wordpress-draft-handoff`
- `POST /api/content/work-items/wordpress-draft-execution`
- `POST /api/content/work-items/measurement-window`
- `POST /api/content/work-items/measurement-outcome`

</allowed_endpoints>

## Kontrakt dowodów

<evidence_requirements>

Każda rekomendacja musi mieć identyfikatory dowodów i identyfikatory źródeł danych z WILQ API. Brak dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak preflightu, briefu sprzedażowego, rejestr twierdzeń, human review, audytu albo measurement window oznacza blokadę odpowiedniego kroku.

Adres `ekologus.dev.proudsite.pl` może być tylko preview/design/staging context. Nie używaj go jako final canonical, historycznego SEO evidence ani measurement target.

</evidence_requirements>

## Kontrakt odpowiedzi

<output_contract>

Trzymaj się `references/output-contract.md`. Odpowiedź ma prowadzić Wilka przez jedną bezpieczną sesję pracy: status, dowody, kolejka treści, diagnoza, sprawdzenie w WILQ, akcje do sprawdzenia, blokady i następny krok.

Kontrakt językowy: wszystkie odpowiedzi dla operatora pisz po polsku z polskimi znakami. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory work itemów, identyfikatory akcji, ścieżki endpointów i wartości enumów zostaw bez zmian.

</output_contract>

## Kontrakt bezpieczeństwa

<safety_rules>

<!-- no-invented-metrics guardrail: do not invent metrics. -->
<!-- Polish language contract: operator-facing responses must be in Polish with Polish diacritics. -->

- Nie wymyślaj metryk, fraz, pozycji, danych GSC, danych GA4, gapów Ahrefs, twierdzeń ani statusów WordPress.
- Nie pisz finalnego artykułu bez WILQ API structured draft runtime i strict schema.
- Nie wywołuj OpenAI SDK bezpośrednio; produkcyjne generowanie przechodzi przez WILQ API.
- Nie wywołuj WordPress bezpośrednio; handoff przechodzi przez WILQ API i pozostaje draft-only.
- Nie ustawiaj ani nie akceptuj `publish_ready=true`.
- Nie pomijaj preflightu, briefu sprzedażowego, rejestr twierdzeń, quality review, human review, audytu ani measurement window.
- Nie traktuj blokad jako rekomendacji. Przepisz je na najmniejszy bezpieczny krok naprawczy.
- Nie publikuj, nie aktualizuj destrukcyjnie i nie obiecuj efektów SEO, leadów ani sprzedaży przed gotowym pomiarem.

</safety_rules>
