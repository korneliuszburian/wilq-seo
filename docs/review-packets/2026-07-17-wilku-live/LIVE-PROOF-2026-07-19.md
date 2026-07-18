# WILQ — aktualny dowód live dla marketera

Odczyt: 19 lipca 2026, lokalny WILQ API `127.0.0.1:8000`. To jest dowód
odczytu i działania workflow, nie UAT Wilka ani zgoda na publikację.

## Co jest dostępne

- 12 konektorów w katalogu; 9 skonfigurowanych, 2 wymagają dostępu.
- WordPress inventory: 808 adresów, publiczna mapa 808/808 w limicie 2000.
- Treściowy workflow pokazuje pełny katalog, exact URL, materiał WordPress,
  sekcje, metryki i dopasowane karty usług; nic nie wybiera się automatycznie.
- BDO i doradztwo/outsourcing używają tego samego kontraktu planowania.
- Korpus materiałów Ekologusa: 7/15 kontrolowanych materiałów jest dostępnych
  jako zredagowane, lineage-bound fakty; 8/15 pozostaje `import_pending`.

## Dwa exact przypadki

### BDO

- URL: `https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/`
- Karta: `ekologus_service_bdo_reporting`.
- Aktualne wejście: GSC exact page, 266 wyświetleń, 1 kliknięcie, CTR 0,38%.
- 18/19 lipca uruchomiono jedną nową wersję planu na aktualnym digest:
  proposal v5, 12 sekcji, 7 materiałów i 4 karty wiedzy. Stary zapis został
  zastąpiony przez exact, świeży fixed point; nie jest mieszany z nowym wejściem.
- Operator potwierdził zakres i mapę sekcji, a następnie uruchomiono pełny draft:
  `content_revision_f942b8008f99493693eb991050a074f5`, 5 sekcji, 3 FAQ, 2 CTA,
  1 link wewnętrzny, 7 materiałów i 4 karty wiedzy. Draft pozostaje
  `publish_ready=false` i nie wykonuje zapisu do WordPressa.

### Doradztwo i outsourcing

- URL: `https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/`
- Karta: `ekologus_service_environmental_consulting_outsourcing`.
- Aktualny plan: v6, exact input digest, 7 materiałów Ekologusa i 4 karty
  wiedzy w top-level oraz w sekcjach.
- Trwała rewizja v2 zawiera title, meta, H1, lead, sekcje, FAQ, CTA,
  linkowanie i te same identyfikatory materiałów; pozostaje niezatwierdzona.
- Semantic review zatrzymuje się na typed blockerze
  `storage_activation_required`: immutable storage wymaga backupu i maintenance
  window. Nie udajemy review ani jakości 10/10.

## Deterministyczna bramka jakości obu exact rewizji

- BDO: rewizja `content_revision_f942b8008f99493693eb991050a074f5`, digest
  `8ba6d11935ac8ab1f498c68fa291a2818045bd1372b594a9d4a28c697644db8e`;
  wynik `blocked`, findings: `sales_brief_signal_review_required`,
  `missing_measurement_window`.
- Doradztwo i outsourcing: rewizja `content_revision_4d9558f60b1b462b9ae49d5caeb73da7`,
  digest `b096a52901e8e4bb467f3fc8e9286b547643045eeb62872bb86c753ccf19396c`;
  ten sam wynik i te same findings.
- Oba review są związane z exact rewizją i nie zatwierdzają tekstu. Brak okna
  pomiarowego nie jest dopowiadany ani zastępowany obietnicą wyniku.

## Jedna decyzja produktu

Marketer nie wybiera dziesięciu wersji. WILQ prowadzi do jednego aktualnego
planu i jednej exact rewizji. Starsze propozycje są historią albo `stale`, a
warianty mogą służyć wyłącznie wewnętrznemu challenger review.

## Czego ten dowód nie potwierdza

- Nie jest to werdykt Wilka ani realny UAT.
- Nie potwierdza jakości tekstu, skuteczności CTR, konwersji ani wzrostu.
- Nie daje zgody na WordPress write/publikację.
- Nie zamyka maintenance window, owner review kart ani importu pozostałych
  materiałów.
