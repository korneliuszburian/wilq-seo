# Pakiet review daily-check dla Wilku — 2026-08-16

Rola dokumentu: `current state` pakietu review dla marketera (Bead `wilq-seo-v9ab.13`).
Nie jest publikacją, decyzją ani dowodem UAT. Pokazuje dokładnie to, co WILQ
zwraca live przez `/api/marketing/daily-check` w dniu generowania; brak świeżego
odczytu = jawny blocker, nigdy zgadywana metryka.

## Werdykt dnia (live API, 2026-08-16)

Daily-check zwrócił **4 zablokowane rekomendacje** — wszystkie z powodu braku
świeżego, potwierdzonego odczytu źródła. To jest poprawny stan fail-closed:
WILQ nie pokazuje liczb ani wniosków bez dowodu.

| Priorytet | Rekomendacja | Stan | Dowody | Źródła |
|---|---|---|---|---|
| 5 | Napraw Google Ads OAuth zanim padną wnioski o kosztach | blocked | 12 | google_ads |
| 10 | Przejrzyj kolejkę problemów Merchant Center | blocked | 12 | google_merchant_center |
| 12 | Przejrzyj kolejkę SEO z GSC i WordPress | blocked | 10 | ahrefs, gsc, wordpress×2, ga4 |
| 14 | GA4: pomiar i jakość ruchu do kontroli | blocked | 2 | google_analytics_4 |

Łącznie daily-check ma 34 evidence IDs; `safe_next_actions=[]`, `do_not_touch=[]`
— WILQ nie proponuje żadnej akcji dopóki źródła nie mają świeżego odczytu.

## Blokery (czego WILQ NIE potwierdza)

- Brak świeżego odczytu vendorów: każda rekomendacja mówi wprost
  „Najpierw potwierdź źródło, dowód i świeżość w WILQ".
- Żadna metryka kosztów/ROAS/konwersji nie jest pokazana jako aktualna.
- Żaden write: `do_not_touch=[]` i brak ActionObjectów do review.

## Pytania do Wilku (3–5)

1. Czy komunikat „źródło nie ma świeżego odczytu" jest dla Ciebie zrozumiały,
   czy brzmi jak awaria?
2. Czy kolejność rekomendacji (Ads OAuth → Merchant → SEO → GA4) odpowiada
   Twoim priorytetom dnia?
3. Czego brakuje w daily-check, żebyś mógł z niego pracować po odświeżeniu
   źródeł?
4. Czy chcesz, żeby WILQ pokazywał „ostatnia znana wartość" przy zablokowanym
   odczycie (obecnie pokazuje tylko blocker)?

## Jak odświeżyć źródła (operator, po urlopie)

```bash
# read-only refreshe przez API (nie vendor write):
curl -X POST http://127.0.0.1:8000/api/jobs/configured_vendor_read_refresh/run \
  -H 'Content-Type: application/json' -d '{"reason": "daily-check review"}'
# albo pojedynczo: /api/connectors/{id}/refresh
```

Po odświeżeniu daily-check zwróci rekomendacje z liczbami; ten pakiet można
wygenerować ponownie. Refresh jest read-only (vendor_read); nie ma żadnego
zapisu po stronie dostawcy.

## Czego nie udajemy

Ten pakiet NIE jest UAT. Jest snapshotem stanu API do rozmowy z Wilku.
Weryfikacja użyteczności wymaga sesji Wilku na świeżym daily-checku.
