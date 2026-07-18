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
- API prawidłowo oznacza zapisany starszy plan jako `stale`; nie pokazuje go jako
  aktualnego planu do review i nie pozwala zatwierdzić jego mapy sekcji.
- Następny krok: odświeżyć zakres po ponownym potwierdzeniu usługi i uruchomić
  jedną nową wersję planu.

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
