# Handoff — `v9ab.13` review pakietu daily-check

Data przygotowania: 2026-07-13 Europe/Warsaw

## Status

To jest aktualny materiał do realnego review Wilku/operatora. Nie jest to
zapisana sesja UAT i nie zawiera zmyślonego uczestnika, czasu ani werdyktu.

## Aktualny dowód API

Źródło znaczenia: `GET /api/marketing/daily-check`.

Ostatni odczyt live:

- `status=blocked`;
- `freshness.state=fresh`;
- 7 source connectors w odpowiedzi;
- 23 evidence IDs;
- 1 blocked recommendation;
- 3 safe next actions;
- 1 element `do_not_touch`.

Nie interpretuj tych liczb jako sukcesu marketingowego. To opis kolejki pracy
i jej ograniczeń. Szczegóły, identyfikatory dowodów, reguł i akcji Wilku ma
sprawdzić bezpośrednio w WILQ/API, nie w tym skrócie.

## Jak wygenerować świeży packet

```bash
rtk uv run python scripts/export_marketer_uat_packet.py \
  --api-base http://127.0.0.1:8000 \
  --format markdown
```

Packet contract: `ekologus_marketer_uat_packet_v1`. Obejmuje 5 widoków:
Centrum pracy, Merchant, Treści, Google Ads i GA4 oraz 5 pytań końcowych.

## Pytania do review

1. Czy wiesz, co zrobić jako następny krok?
2. Który widok dał Ci największy realny zysk?
3. Gdzie musiałeś zgadywać znaczenie statusu albo pola?
4. Czy Treści oszczędzają czas przy decyzji: zachować, odświeżyć, scalić?
5. Ile czasu realnie oszczędza ta ścieżka: 0, 15, 30 czy 60+ minut?

## Format wyniku

Po sesji trzeba zapisać: `reviewer`, datę/czas, zakres, wybrany item, decyzję
`ready`/`needs_follow_up`/`defer`, czas przejścia, punkty konfuzji, brakujące
dowody, ocenę użyteczności 1–10 i follow-up Beads. Werdykt musi wskazywać
aktualne evidence IDs/source connectors/rule IDs albo jawnie opisać, czego
reviewer nie mógł sprawdzić.

Do czasu uzupełnienia tych pól `v9ab.13` pozostaje otwarty. Nie zamieniaj
packetu, screenshotu ani zielonego testu w dowód UAT.
