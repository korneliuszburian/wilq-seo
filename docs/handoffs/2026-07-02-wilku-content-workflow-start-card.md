# Content Workflow - co pokazać Wilkowi

## Krótko

WILQ umie już uczciwie poprowadzić jeden realny temat przez bramki workflowu:
widzi kandydatów, wybiera ten, który ma dowody i pozwala tylko na planowanie.
Nie udaje, że ma gotowy brief, szkic albo publikację w WordPressie.

To jest dobre jako ekran kontroli procesu, ale jeszcze nie jako produkcyjna
maszyna do pisania tekstów.

## Aktualny stan

- Kolejka treści: `blocked`.
- Kandydaci: 3.
- Kandydaci gotowi do pracy: 1.
- Aktywny temat: `SEO: odśwież lub scal "ekologus" (24 zapytań)`.
- Work item: `content_work_item_content_decision_https___www_ekologus_pl`.
- Preflight: `plan_allowed`, czyli można planować.
- Sales Brief: zablokowany.
- Draft package: zablokowany.
- Structured draft generation: zablokowane.
- Human review: wymagany.
- WordPress draft-only handoff: zablokowany.
- Measurement window: zaplanowane, najwcześniejszy werdykt `2026-08-01`.

## Dowody

- `ev_refresh_refresh_google_search_console_9b25d4143bea`
- `ev_refresh_refresh_wordpress_ekologus_691cbe6ab27d`

## Ocena użyteczności

- 7.5/10 jako uczciwa kontrola procesu end-to-end.
- 4.5/10 jako gotowość do produkcyjnego szkicu.
- 8.5/10 jako blokada fałszywych claimów i zapisów.

## Co jest dobre

- Wilku od razu widzi, że tylko jeden kandydat przeszedł bramki.
- Ekran pokazuje, że można planować, ale nie wolno jeszcze pisać ani wysyłać do
  WordPressa.
- Workflow nie zamienia problemów pomiaru albo braków wiedzy w fałszywe tematy
  do produkcji.

## Czego nie obiecywać

- Nie mówić, że mamy gotowy produkcyjny szkic.
- Nie mówić, że można publikować w WordPressie.
- Nie mówić, że odświeżenie da efekt SEO, leady, konwersje albo przychód.
- Nie mówić, że temat jest bezpieczny bez Claim Ledger i human review.

## Następny sensowny krok

Podpiąć pełny Claim Ledger jako widoczną bramkę szkicu i przepuścić jeden temat
z zatwierdzoną wiedzą `approved_current` przez ścieżkę:

`preflight -> Sales Brief -> Claim Ledger -> draft-only package -> human review`.
