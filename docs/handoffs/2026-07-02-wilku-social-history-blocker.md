# Social history blocker - co pokazać Wilkowi

## Krótko

WILQ może przygotować kierunki postów LinkedIn/Facebook tylko jako review-only.
Nie może publikować i nie może twierdzić, że temat nie powiela wcześniejszych
postów, dopóki nie ma historii social.

To jest poprawne zachowanie: WILQ ma nie generować pewności z braku danych.

## Aktualny stan

- LinkedIn: `missing_credentials`.
- Facebook: `missing_credentials`.
- `publish_allowed=false`.
- `historical_social_inventory_status=missing`.
- `duplicate_risk_status=blocked_until_social_history_review`.
- Tryb: `review_only`.

## Co działa

- Akcje szkicu do sprawdzenia są zwalidowane:
  - `act_prepare_linkedin_social_drafts`
  - `act_prepare_facebook_social_drafts`
- WILQ może użyć source inputs z GSC, Merchant i WordPress jako dowodów do
  kierunku posta.
- WILQ blokuje claim `brak powtórzeń historycznych postów`.

## Czego brakuje

Potrzebny jest metadata-only spis historii LinkedIn/Facebook:

- `channel`
- `published_at`
- `topic`
- `service`
- `claim`
- `cta`
- `format`
- `post_url_or_id`
- `source_evidence_id`

Raw treści postów i komentarze nie są wymagane na start. Wystarczy metadane,
żeby sprawdzić duplikację tematu, claimu, CTA i kąta komunikacji.

## Wynik evala

- Eval artifact: `.local-lab/evals/codex-skill/20260702T120859Z`.
- `operator_usefulness_score=5`.
- `failure_tags=[]`.
- Wszystkie hard gates: true.

## Następny krok

Zebrać metadata-only historię LinkedIn/Facebook i podpiąć ją jako kontrakt
`social_history_inventory_v1`. Do tego czasu social pozostaje review-only.
