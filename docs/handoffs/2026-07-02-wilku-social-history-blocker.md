# Historia social - co blokuje powtórki

## Krótko

WILQ może przygotować kierunki postów LinkedIn/Facebook tylko do oceny.
Nie może publikować i nie może twierdzić, że temat nie powiela wcześniejszych
postów, dopóki nie ma historii LinkedIn/Facebook.

To jest poprawne zachowanie: WILQ ma nie generować pewności z braku danych.

## Aktualny stan

- LinkedIn: `missing_credentials`.
- Facebook: `missing_credentials`.
- `publish_allowed=false`.
- `historical_social_inventory_status=missing`.
- `duplicate_risk_status=blocked_until_social_history_review`.
- Tryb techniczny: `review_only`.

## Co działa

- Akcje szkicu do sprawdzenia są zwalidowane:
  - `act_prepare_linkedin_social_drafts`
  - `act_prepare_facebook_social_drafts`
- WILQ może użyć danych z GSC, Merchant i WordPress jako dowodów do
  kierunku posta.
- WILQ blokuje twierdzenie `brak powtórzeń historycznych postów`.

## Czego brakuje

Potrzebny jest spis historii LinkedIn/Facebook w formie samych metadanych:

- `channel`
- `published_at`
- `topic`
- `service`
- `claim`
- `cta`
- `format`
- `post_url_or_id`
- `source_evidence_id`

Pełne treści postów i komentarze nie są wymagane na start. Wystarczą metadane,
żeby sprawdzić duplikację tematu, claimu, CTA i kąta komunikacji.

## Jak przygotować input

WILQ ma teraz audyt historii social tylko do odczytu. Wygeneruj aktualny format:

```bash
rtk uv run python scripts/social_history_inventory_audit.py --print-input-example > .local-lab/proof/social-history-input-YYYYMMDD.json
```

Po uzupełnieniu metadanych sprawdź plik wejściowy:

```bash
rtk uv run python scripts/social_history_inventory_audit.py .local-lab/proof/social-history-input-YYYYMMDD.json --format markdown
```

Audyt odrzuca pełne treści postów, komentarze, dane użytkowników i tokeny.
Status `review_ready` oznacza tylko gotowość do oceny powtórek. Nadal nie wolno
mówić, że temat jest nowy albo bez powtórek, dopóki ocena nie porówna tematu,
claimu, CTA i formatu z historią.

## Wynik testu jakości

- Artefakt testu: `.local-lab/evals/codex-skill/20260702T120859Z`.
- `operator_usefulness_score=5`.
- `failure_tags=[]`.
- Wszystkie twarde bramki: true.

## Następny krok

Zebrać historię LinkedIn/Facebook jako same metadane i podpiąć ją jako kontrakt
`social_history_inventory_v1`. Do tego czasu social pozostaje tylko do oceny.
