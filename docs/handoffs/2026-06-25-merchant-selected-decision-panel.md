# Merchant Selected Decision Panel - 2026-06-25

## Zakres

Dodano pierwszy marketer-facing panel w `/merchant` przed pełnym drilldownem.
Panel kondensuje aktualne WILQ API `/api/merchant/diagnostics` do jednej
decyzji feedu:

- co sprawdzić teraz;
- dlaczego problem ma znaczenie;
- jaki jest bezpieczny następny krok;
- co oznaczają liczby;
- jakie dowody i źródła wspierają decyzję;
- czego WILQ nie zrobi teraz;
- czego brakuje;
- jak później sprawdzić efekt.

## Aktualny odczyt API

Źródło: `GET http://127.0.0.1:8000/api/merchant/diagnostics`.

Pierwsza decyzja:

- `merchant_decision_pl_disapproved_landing_page_error_n_link_merchant_action`
- problem: `landing_page_error`
- atrybut: `n:link`
- kraj: `PL`
- raporty tej decyzji: `9`
- największy raport: `3`
- konteksty: `3`
- semantyka: `reported_issue_occurrences`, czyli nie unikalne SKU ani gotowa
  lista zmian feedu.

Źródła i dowody:

- `google_merchant_center`
- `ev_refresh_refresh_google_merchant_center_6dbd43a93f93`

## UX Decision

Pierwszy ekran nie używa teraz `ActionObject review`, `payload preview`,
`feed write`, `approval` ani `price-impact` jako normalnego języka marketera.
Zamiast tego pokazuje:

- `akcja do walidacji`;
- `podgląd zmian`;
- `ręczny przegląd`;
- `zapis do feedu`;
- `zatwierdzenie produktu`;
- `wpływ ceny`.

Techniczne ID, kontrakty i traceability zostają dostępne niżej, ale nie są
językiem pierwszej decyzji.

## Proof

Browser proof:

- `.local-lab/proof/merchant-selected-decision-panel-20260625/page-text.txt`
- `.local-lab/proof/merchant-selected-decision-panel-20260625/screenshot-1782368758722.png`

Focused verification:

- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk pnpm --filter @wilq/dashboard test -- MerchantDiagnosticSurface --testTimeout=10000`

## Residual Risk

Niższy, współdzielony action-focus/detail layer nadal może pokazywać techniczne
`apply` albo raw blocked-claim wording. To nie blokuje pierwszego ekranu
Merchant, ale powinno wejść jako osobny dashboard-copy hardening task dla
shared action components.
