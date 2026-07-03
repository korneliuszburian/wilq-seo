# Claim Ledger w workflow treści - co pokazać Wilkowi

## Krótko

WILQ nie tylko mówi już "szkic zablokowany". Pokazuje teraz bramkę Claim
Ledger: które twierdzenia wolno użyć w szkicu, które wymagają oceny i które
zostają poza treścią.

To jest ważne, bo marketer może odróżnić brak gotowości procesu od realnego
zakazu użycia konkretnych claimów.

## Co się zmieniło

- Snapshot workflowu API zawiera teraz `claim_ledger`.
- `/content-workflow` pokazuje panel `Claim Ledger: co wolno powiedzieć`.
- Panel rozdziela claimy na:
  - `Do szkicu`,
  - `Wymaga oceny`,
  - `Zablokowane`,
  - `Wymagane`.
- Kontrola jakości z dashboardu wysyła teraz realny `claim_ledger`, a nie
  `null`.

## Dowód techniczny

- Zadanie treściowe: `content_work_item_content_decision_https___www_ekologus_pl`.
- Claim Ledger:
  `claim_ledger_content_work_item_content_decision_https___www_ekologus_pl`.
- Liczba twierdzeń w aktualnym podglądzie: 1.
- Status pierwszego claimu: `allowed_with_evidence`.
- Dowód pierwszego claimu:
  `ev_refresh_refresh_google_search_console_9b25d4143bea`.

## Co nadal blokuje produkcję

- Ledger jest widoczny, ale produkcyjna gotowość wymaga jeszcze wiedzy
  zatwierdzonej do finalnych treści.
- Sales Brief, paczka szkicu, uporządkowane generowanie, ocena człowieka i
  przekazanie do WordPressa dalej pozostają bramkami.
- Nie twierdzimy efektu SEO, leadów, konwersji ani przychodu bez okna pomiaru.

## Następny krok

Przepuścić jeden temat z realnie zatwierdzoną wiedzą przez:

`preflight -> Sales Brief -> Claim Ledger -> paczka szkicu bez publikacji -> ocena człowieka`.
