# Handoff — 2026-07-13: Ahrefs manual decision first

## Domknięty slice

`wilq-seo-3bst.7` przeniósł istniejący, typed `gap_read_contract` przed galerię
kart na `/ahrefs`. Gdy `cross_check_status=manual_required`, marketer najpierw
widzi decyzję „Najpierw zweryfikuj GSC i WordPress”, status odczytu danych,
liczbę tematów do ręcznej oceny, potwierdzenia GSC/WordPress, podsumowanie
dowodów i safe next step.

To jest wyłącznie render istniejącego API view-modelu. Nie dodano endpointu,
matcherów w React, ActionObjectu, write path ani publikacji. `gotowe` oznacza
gotowość danych Ahrefs, nie gotowość briefu ani publikacji.

## Aktualny dowód

- Live `/api/ahrefs/diagnostics`: `manual_required`, 6 kandydatów, 0 exact GSC,
  0 exact WordPress, 0 akcji; evidence pozostaje Ahrefs-only.
- Dashboard test: `apps/dashboard/src/routes/App.test.tsx`, 32/32.
- Dashboard lint i build przechodzą.
- Desktop 1440×900:
  `.local-lab/proof/3bst7-ahrefs/ahrefs-desktop-final.png`.
- Mobile 390×844:
  `.local-lab/proof/3bst7-ahrefs/ahrefs-mobile-final.png`; `scrollWidth=390`.
- Re-review marketer/operator: 7/10. Pierwszy viewport odpowiada: „czy mogę
  tworzyć brief?” — nie, najpierw ręczny cross-check; szczegółowe karty są
  kontekstem poniżej decyzji.

## Nie cofaj

- Nie zmieniaj `manual_required` na `blocked`: odczyt Ahrefs jest gotowy, ale
  semantyczna decyzja wymaga człowieka.
- Nie buduj dopasowania GSC/WordPress w React ani nie twórz akcji dla weak/missing
  similarity.
- Nie pokazuj evidence/action IDs w pierwszym viewportcie.

## Następny slice

`wilq-seo-c9h9.17`: endpoint Ahrefs jest użyteczny semantycznie, ale realnie
wolny (kolejne zdrowe odczyty HTTP: 14.654183 s i 15.872616 s). Zmierz call
graph przez HTTP/runtime, potem zastosuj najwęższy istniejący cache/prewarm seam
z inwalidacją przy relevant Ahrefs refreshu oraz inputach GSC/WordPress. Nie
osłabiaj freshness/evidence i nie dodawaj nowego endpointu.
