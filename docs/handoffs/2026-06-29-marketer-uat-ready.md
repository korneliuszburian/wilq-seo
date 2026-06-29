# Pakiet UAT marketera gotowy - 2026-06-29

Status: gotowe do realnej sesji z marketerem, ale UAT nie jest jeszcze
wykonany.

## Co jest gotowe

- Lokalny WILQ API i dashboard były dostępne przy generowaniu pakietu.
- Eksporter pakietu UAT czyta aktualne powierzchnie WILQ API dla:
  - Centrum pracy
  - Merchant
  - Treści
  - Google Ads
  - GA4
- Markdown pakietu pokazuje czytelną ścieżkę sesji i kartę odpowiedzi po
  polsku, bez surowych bloków JSON.
- JSON pakietu pozostaje formatem maszynowym dla automatyzacji i zapisu
  wyniku, nie główną formą czytania przez marketera.
- Rejestrator wyniku przyjmuje tylko kanoniczny polski kształt odpowiedzi.

## Wygeneruj aktualny pakiet

Uruchom z katalogu repo:

```bash
rtk uv run python scripts/export_marketer_uat_packet.py \
  --api-base http://127.0.0.1:8000 \
  --format markdown > .local-lab/proof/marketer-uat-packet-$(date +%Y%m%d).md

rtk uv run python scripts/export_marketer_uat_packet.py \
  --api-base http://127.0.0.1:8000 \
  --format json > .local-lab/proof/marketer-uat-packet-$(date +%Y%m%d).json
```

Wygenerowany pakiet w `.local-lab/` jest materiałem dowodowym z live API, nie
źródłem do commita.

## Przeprowadź sesję

Otwórz:

```text
http://127.0.0.1:5173/command-center
```

Daj Wilkowi albo marketerowi 15 minut. Nie tłumacz najpierw statusów. Osoba ma
odpowiedzieć z samego UI:

1. Jaki jest następny krok?
2. Który ekran daje największą realną wartość?
3. Gdzie trzeba było zgadywać znaczenie pola albo statusu?
4. Czy Treści oszczędzają czas przy decyzji, co zachować, odświeżyć albo scalić na
   `ekologus.pl`?
5. Ile czasu to realnie oszczędza: 0, 15, 30 albo 60+ minut?

## Zapisz wynik

Po sesji zapisz wypełniony JSON pod `.local-lab/proof/`, na przykład:

```json
{
  "data": "2026-06-29",
  "osoba": "Wilku",
  "centrum_pracy": "zaliczone <notatka>",
  "merchant": "zaliczone <notatka>",
  "treści": "zaliczone <notatka>",
  "google_ads": "zaliczone <notatka>",
  "ga4": "zaliczone <notatka>",
  "największy_realny_zysk": "<opis>",
  "największa_niejasność": "<opis>",
  "nowe_zadania": ["<zadanie z feedbacku>"],
  "gotowe_bez_developera": "tak"
}
```

Potem uruchom:

```bash
rtk uv run python scripts/record_marketer_uat_result.py \
  .local-lab/proof/marketer-uat-result-20260629.json \
  --format markdown > .local-lab/proof/marketer-uat-result-20260629.md
```

## Sprawdź dowód domknięcia

Przed deklaracją domknięcia Goal 001 uruchom guard:

```bash
rtk uv run python scripts/goal_001_completion_check.py \
  --uat-result .local-lab/proof/marketer-uat-result-20260629.json \
  --format markdown
```

Jeżeli owner jawnie odracza realny UAT zamiast przeprowadzić sesję, zapisz
notatkę JSON pod `.local-lab/proof/`, na przykład:

```json
{
  "odroczenie_realnego_uat": true,
  "data": "2026-06-29",
  "osoba": "<owner>",
  "powód": "<dlaczego UAT jest odroczony>",
  "co_można_pokazać": "<bezpieczny zakres demo>",
  "zablokowane_obietnice": [
    "potwierdzona użyteczność marketera",
    "gotowość bez developera"
  ]
}
```

Potem uruchom:

```bash
rtk uv run python scripts/goal_001_completion_check.py \
  --owner-defer .local-lab/proof/marketer-uat-owner-defer-20260629.json \
  --format markdown
```

## Reguła domknięcia

Goal 001 może deklarować UAT jako domknięty tylko wtedy, gdy spełniony jest
jeden z warunków:

- Istnieje wypełniony wynik realnego UAT marketera i
  `record_marketer_uat_result.py` go waliduje.
- Owner jawnie odracza realny UAT marketera, a notatka mówi:
  - kto odroczył,
  - kiedy,
  - dlaczego,
  - co można bezpiecznie pokazać,
  - jakie obietnice produktu nadal są zablokowane.

Do tego momentu WILQ ma zweryfikowany cleanup gate i gotowy pakiet UAT, ale nie
ma domkniętego dowodu użyteczności.
