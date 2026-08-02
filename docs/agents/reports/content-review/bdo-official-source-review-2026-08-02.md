# BDO — pakiet weryfikacji oficjalnych źródeł

**Data odczytu WILQ:** 2 sierpnia 2026 r.
**Cel:** odblokować przygotowanie tekstu BDO wyłącznie po sprawdzeniu aktualnych propozycji factów z oficjalnych źródeł.
**Status:** **wymaga decyzji eksperta — nie zatwierdzono automatycznie**

## Co blokuje tekst

WILQ ma odczyt aktualnej strony oraz exact sygnały GSC i GA4, ale plan BDO jest zablokowany do czasu pokrycia ośmiu obszarów regulacyjnych zatwierdzonymi factami źródłowymi. Nie zastępuje ich materiałem Ekologus, promptem ani listą słów kluczowych.

Każda pozycja niżej jest zapisaną propozycją, powiązaną z exact snapshotem oficjalnego URL-a. Przyjęcie lub odrzucenie pozostaje decyzją człowieka. Przyjmując pozycję, potwierdzasz tylko to, że zdanie odpowiada wskazanemu źródłu i właściwie ogranicza jego zakres — nie zastępuje to porady prawnej ani kontroli stanu faktycznego klienta.

## Lista do weryfikacji

### 1. Definicja systemu BDO

- **Wymaganie:** definicja systemu BDO (`bdo_definition`)
- **Źródło:** [BDO: O systemie BDO](https://bdo.mos.gov.pl/o-systemie-bdo/)
- **Propozycja factu:** BDO (Baza danych o produktach i opakowaniach oraz o gospodarce odpadami) to zintegrowany system teleinformatyczny obejmujący Rejestr-BDO oraz moduły ewidencji i sprawozdawczości.
- **Ślad WILQ:** proposal `regulatory_source_fact_proposal_aca370796093d7a8f5e4b163`; snapshot `regulatory_snapshot_1892e6427073cc4a87ad1ed6`; digest `c558215dd815c94c467023f8ceb27791cd205d5b673cdd1ef60c5423e0202d70`; run `codex_regulatory_source_fact_7bcd670cc6f84cd79860ceb8c465fa31`.

### 2. Kogo może dotyczyć wpis do BDO

- **Wymaganie:** zakres podmiotów (`bdo_registration_scope`)
- **Źródło:** [BDO: Podmioty zobowiązane do rejestracji w BDO](https://bdo.mos.gov.pl/news/podmioty-zobowiazane-do-rejestracji-w-bdo/)
- **Propozycja factu:** Obowiązek wpisu do Rejestru BDO obejmuje m.in. podmioty, które wytwarzają odpady i prowadzą ich ewidencję, a także wskazanych wprowadzających produkty lub opakowania na terytorium kraju; źródło podaje przykładową, niewyczerpującą listę takich podmiotów.
- **Ślad WILQ:** proposal `regulatory_source_fact_proposal_833c72cd7726ac6d33ad7cce`; snapshot `regulatory_snapshot_3b5e9a39d9c5f39335183b9f`; digest `afec1c0ae89cccc229c5a60c2c12866c9bd44a9053ed0dc57b78d4d599d2e15c`; run `codex_regulatory_source_fact_34fd97a325324dbc925e0e47bc57ed29`.

### 3. Wyłączenia z wpisu lub ewidencji

- **Wymaganie:** wyłączenia (`bdo_exemptions`)
- **Źródło:** [BDO: Zasady rejestracji i wyłączenia](https://bdo.mos.gov.pl/zasady-rejestracji/)
- **Propozycja factu:** W zasadach rejestracji BDO przewidziano zwolnienie z wpisu, dlatego obowiązek rejestracyjny nie dotyczy każdego podmiotu w identycznym zakresie; zastosowanie wyłączenia zależy od spełnienia właściwych warunków ustawowych.
- **Ślad WILQ:** proposal `regulatory_source_fact_proposal_6213d280a5f8abf4207cb965`; snapshot `regulatory_snapshot_e3403ccc29d39c7264a18b27`; digest `2088290cf013adac31085bc87ea44a7220c68b4ad7f6124208a9a2b56ac0ee48`; run `codex_regulatory_source_fact_a9debaf69a9b49098ddc319fe5510bd4`.

### 4. Wpis i aktualizacja danych

- **Wymaganie:** wpis i aktualizacja BDO (`bdo_registration_and_updates`)
- **Źródło:** [BDO: Pamiętaj o aktualizacji danych w BDO](https://bdo.mos.gov.pl/news/przedsiebiorco-pamietaj-o-aktualizacji-danych-w-bdo/)
- **Propozycja factu:** Każdy podmiot wpisany do rejestru BDO ma obowiązek złożyć wniosek o aktualizację wpisu w ciągu 30 dni od zmiany danych lub zakresu działalności; rozszerzenie działalności o wskazane w źródle zakresy może wymagać uiszczenia opłaty rejestrowej.
- **Ślad WILQ:** proposal `regulatory_source_fact_proposal_7f5bd9d97cb4985ac3b74d39`; snapshot `regulatory_snapshot_6c783df0b7ba0b4008ac0128`; digest `c8773ff5f9aa68f597b2bdef1d1dfb1db3fc3f2564b05a36ef706942ae4544ed`; run `codex_regulatory_source_fact_8b4da2edf58542c98a5d386eef8aa379`.

### 5. KPO przed transportem

- **Wymaganie:** ewidencja i KPO (`bdo_records_and_kpo`)
- **Źródło:** [BDO: Kto i kiedy wystawia KPO?](https://bdo.mos.gov.pl/baza-wiedzy/co-w-sytuacji-w-ktorej-podmiot-przekazujacy-odpady-nie-wystawi-kpo/)
- **Propozycja factu:** Zgodnie z przytoczoną treścią art. 69 ust. 1 ustawy o odpadach posiadacz przekazujący odpady sporządza KPO przed rozpoczęciem transportu; niewystawienie KPO oznacza brak możliwości transportu i przekazania tych odpadów.
- **Ślad WILQ:** proposal `regulatory_source_fact_proposal_d5d8233c0f656b3a5ef1360b`; snapshot `regulatory_snapshot_07b821bccfc3c7b9e4c82ce5`; digest `52279ff65d1efaacd6e147cac5460d78c610b247a2991d28c13abcf4a597596d`; run `codex_regulatory_source_fact_4c426124f5814eefa6898a1fa62f388e`.

### 6. Terminy sprawozdań

- **Wymaganie:** sprawozdawczość BDO (`bdo_reporting`)
- **Źródło:** [BDO: Rodzaje i terminy sprawozdań](https://bdo.mos.gov.pl/wp-content/uploads/2023/03/BDO_SPR_IS-Nawigacja-Modul-Sprawozdawczosc-wersja-1.1.pdf)
- **Propozycja factu:** Instrukcja modułu Sprawozdawczość BDO wskazuje, że termin złożenia sprawozdania za poprzedni rok kalendarzowy zależy od jego typu i przypada — dla typów ujętych w tabeli — do 15 marca albo do 31 stycznia.
- **Ślad WILQ:** proposal `regulatory_source_fact_proposal_408371fe2ad2bc0794210993`; snapshot `regulatory_snapshot_6613e498feb18a2d3ea910aa`; digest `0b98c3a16e876a935f59b9c457cc114c922f415c9b2ec7146e64b7e1047582ff`; run `codex_regulatory_source_fact_d9194905d5c24649b2b5b1f1acea8530`.

### 7. Dokumentacja poza BDO

- **Wymagania:** wyłączenia; ewidencja i KPO (`bdo_exemptions`, `bdo_records_and_kpo`)
- **Źródło:** [BDO: Dokumentacja przy awarii, braku Internetu lub energii](https://bdo.mos.gov.pl/baza-wiedzy/co-zrobic-w-przypadku-braku-energii-elektrycznej-awarii-internetu-lub-stalego-braku-dostepu-do-internetu/)
- **Propozycja factu:** Według źródła brak energii elektrycznej albo stały lub czasowy brak dostępu do Internetu nie stanowi awarii BDO i po 30 czerwca 2020 r. nie upoważnia do wystawiania papierowych dokumentów ewidencji odpadów; dokumenty, np. KPO/KPOK, można zaplanować i wygenerować wcześniej.
- **Ślad WILQ:** proposal `regulatory_source_fact_proposal_7c3739ecaf6d45d48dfa80e6`; snapshot `regulatory_snapshot_c92af31c0a8cc3aef6754007`; digest `5ba0a19546cc8f20d278a69fc89611eee634e8cb609d43c30a7a1817ce5d741e`; run `codex_regulatory_source_fact_72bc5822ba5e40ca99e4cd2d156654a6`.

### 8. KPO a KPOK

- **Wymaganie:** ewidencja i KPO (`bdo_records_and_kpo`)
- **Źródło:** [BDO: Odpady komunalne — KPO czy KPOK?](https://bdo.mos.gov.pl/news/odpady-komunalne-kpo-czy-kpok/)
- **Propozycja factu:** Podmioty odbierające lub zbierające odpady komunalne oraz prowadzący PSZOK są zobowiązani do ewidencjonowania odpadów w systemie BDO; przed przekazaniem odpadów należy sporządzić elektronicznie KPO albo KPOK, przy czym przytoczony tekst nie rozstrzyga, który dokument stosuje się w konkretnej sytuacji.
- **Ślad WILQ:** proposal `regulatory_source_fact_proposal_5bb3a2e57fabf9716fe5b559`; snapshot `regulatory_snapshot_3e68586e0fa7a626a5d0812a`; digest `b4819d0dbf559631b2309f887c6346738e591add089b9c1bc4e0cdcee99302c4`; run `codex_regulatory_source_fact_cb03986afdd045a785cb503717320e71`.

### 9. Dostęp do konta BDO

- **Wymaganie:** dostęp do konta BDO (`bdo_access_and_account`)
- **Źródło:** [BDO: Logowanie i uwierzytelnienie użytkowników systemu](https://bdo.mos.gov.pl/news/logowanie-do-systemu-bdo-i-uwierzytelnienie-uzytkownika-poprzez-krajowy-wezel-identyfikacji-elektronicznej/)
- **Propozycja factu:** Dostęp do systemu BDO wymaga potwierdzenia tożsamości przez Login.gov.pl; użytkownik główny ma dostęp do wszystkich dostępnych modułów i może dodawać użytkowników, natomiast użytkownik podrzędny ma dostęp do Modułu ewidencji w zakresie wskazanym w źródle.
- **Ślad WILQ:** proposal `regulatory_source_fact_proposal_28010e9e9dc852085e16cab0`; snapshot `regulatory_snapshot_5f3498649a0b333d52870ff9`; digest `cad9b6d712eb85fe1804a67e5b01ff103ce42685edc5351ce3ff7f4085e34f62`; run `codex_regulatory_source_fact_c454f883eca04c51a4c9b593de36e565`.

### 10. Ryzyka i sankcje

- **Wymaganie:** ryzyka i sankcje (`bdo_risks_and_sanctions`)
- **Źródło:** [BDO: Sankcje za działanie niezgodne z przepisami](https://bdo.mos.gov.pl/baza-wiedzy/jakie-groza-sankcje-karne-podmiotom-zobowiazanym-do-uzyskania-wpisu-do-rejestru-bdo-za-dzialanie-niezgodne-z-przepisami/)
- **Propozycja factu:** Źródło wskazuje, że za wybrane naruszenia obowiązków związanych z Rejestrem-BDO mogą grozić kary aresztu albo grzywny oraz administracyjne kary pieniężne, w podanych przypadkach od 1 000 zł do 1 000 000 zł, a przy transporcie odpadów bez wpisu od 2 000 do 10 000 zł.
- **Ślad WILQ:** proposal `regulatory_source_fact_proposal_b32b9e27255ca6b1a483870d`; snapshot `regulatory_snapshot_b428bc1d128388f8c349ac34`; digest `1c2de4603ea17a3ba151007d565c5ec44733bd39c56628a35a657fe35f44f918`; run `codex_regulatory_source_fact_5b7ed70485814a8aaf80497164338769`.

## Decyzja ekspercka

Dla każdej pozycji wybierz w dashboardzie WILQ **„przyjmij”** tylko gdy:

1. propozycja nie wychodzi poza wskazane źródło;
2. zakres zdania odpowiada requirementowi z tej listy;
3. zdanie nie jest traktowane jako indywidualna porada dla każdej firmy;
4. aktualność źródła jest wystarczająca dla publikowanego materiału.

Odrzuć pozycję i wpisz krótką przyczynę, gdy źródło jest nieaktualne, zbyt szerokie, niepełne albo nie obsługuje zdania. Po pokryciu wszystkich requirementów WILQ odblokuje plan BDO; dopiero potem można utworzyć pierwszy draft. Ten dokument nie potwierdza publikacji, WordPressa, wdrożenia, measurementu ani wyniku SEO.
