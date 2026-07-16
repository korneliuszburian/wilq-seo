# Handoff — `v9ab.13` review pakietu daily-check

Data przygotowania: 2026-07-13 Europe/Warsaw  
Ostatnie odświeżenie materiału: 2026-07-16 Europe/Warsaw

## Status

To jest aktualny materiał do realnego review Wilku/operatora. Nie jest to
zapisana sesja UAT i nie zawiera zmyślonego uczestnika, czasu ani werdyktu.

## Aktualny dowód API

Źródło znaczenia: `GET /api/marketing/daily-check`.

Ostatni odczyt live 2026-07-16:

- `status=blocked`;
- `freshness.state=fresh` po bezpiecznych read-only refreshach Ads, Merchant i
  Localo; blocker nie wynika już ze starych danych;
- 7 source connectors w odpowiedzi;
- 24 evidence IDs;
- 8 expert rules;
- 1 blocked recommendation: review jakości landing page i pomiaru GA4;
- 3 safe next actions;
- 1 element `do_not_touch`.

Świeży packet `ekologus_marketer_uat_packet_v1` wygenerowany 2026-07-16
zawiera dodatkowo:

- 24 zadania w Centrum pracy, z pierwszym krokiem Merchant;
- 1345 zgłoszeń problemów Merchant, 5 widocznych decyzji i 1 akcja do
  sprawdzenia, nadal review-only;
- Treści: 2 decyzje, 1 potwierdzone dopasowanie WordPress i exact homepage
  snapshot dla `https://www.ekologus.pl/`: 29 sygnałów planistycznych GSC,
  47 wyświetleń, 3 kliknięcia oraz jawny blocker, że kontekst usługi nie jest
  zatwierdzony do finalnych treści;
- Ahrefs pozostaje zablokowany do ręcznego cross-checku, bez publicznego URL-a
  i canonicalu;
- Ads: 18 kampanii, 5 widocznych decyzji i 9 akcji do sprawdzenia, bez zapisu
  zmian;
- GA4: 2 jawne problemy pomiaru, 4 decyzje i 1 akcja do sprawdzenia, bez
  interpretacji jako problemu kampanii.

Generator packetu pobiera teraz dla wybranego content itemu kanoniczny
`GET /api/content/work-items/snapshot`, więc nie miesza 31 surowych query z
29 sygnałami planistycznymi widocznymi w dashboardzie. Diagnostyka nadal
dostarcza pozostałe decyzje, w tym ręczny cross-check Ahrefs.

To jest lepszy materiał do sesji niż wcześniejszy skrót, ale nadal nie jest
werdyktem marketera.

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
