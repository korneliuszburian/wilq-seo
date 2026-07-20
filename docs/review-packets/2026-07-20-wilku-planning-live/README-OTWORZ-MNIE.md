# WILQ — aktualny wynik planowania treści

To jest paczka do sprawdzenia przez marketera. Otwórz najpierw:

1. [Plany i metryki](PLANY-I-WYNIKI.md)
2. [Karta decyzji](KARTA-DECYZJI-WILKA.md)

Możesz zobaczyć ten sam workflow na żywo pod:

`http://127.0.0.1:5173/content-workflow`

Wybierz stronę z kolejki i otwórz etap **Strategia**. Dane pochodzą z WILQ
API, nie z ręcznie przepisanej paczki. Techniczny odczyt API:

```text
GET /api/content/work-items/queue?work_item_id={ID}
GET /api/content/work-items/{ID}/planning-proposals
GET /api/content/work-items/{ID}/initial-draft
```

Na tym fixed poincie plany są gotowe, ale pełny tekst nie został uruchomiony:
WILQ czeka na decyzję zakresu. To celowa bramka — nie jest to błąd ani zgoda
na publikację.
