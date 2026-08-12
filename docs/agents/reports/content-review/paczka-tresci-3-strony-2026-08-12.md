# Paczka treści do review — 3 strony Ekologus

Rola dokumentu: `current state` pakietu review dla marketera. Nie jest publikacją ani zapisem decyzji.

## Jak czytać

Trzy pełne rewizje przeszły pipeline WILQ: plan → draft → pre-save readability gate → regulatory assurance → semantic review (9/9 wymiarów). Żadna nie została opublikowana; `publish_ready=false`, `human_review_required=true` dla każdej. Decyzja Wilku zapisuje się przez `POST /draft-revisions/{revision_id}/review` z decyzją `approved` / `needs_changes` / `rejected`.

| Strona | Rewizja | Sekcje | FAQ | CTA | Semantic review |
|---|---|---|---|---|---|
| BDO – co musi wiedzieć przedsiębiorca? | `content_revision_f4c23cfcd5b6449c83281545b4883e2c` | 8 | 3 | 2 | 9/9 strong, 0 findings |
| Szkolenia z ochrony środowiska | `content_revision_66f7eec3ec9646a5a8ed5327a44e3da8` | 7 | 3 | 2 | 9/9 strong, 0 findings |
| Doradztwo i outsourcing ekologiczny | `content_revision_62ef7b61f6fd4a399a41d3ab33094fc9` | 3 | 3 | 1 | 9/9 strong, 0 findings |

## Strony zablokowane (nie w paczce, powód)

- **Dokumentacja środowiskowa w procesie inwestycyjnym** — plan 3x odrzucony przez pipeline (`lineage_mismatch`: Codex używał headingów z inputu w niepoprawnej formie). Fail-closed zadziałał; brak rewizji.
- **Ocena wpływu projektów / BHP i P.POŻ / KIP w praktyce** — brak karty usługi w Service Profile (nie ma dopasowania usługi do tych stron).

---

## BDO – co musi wiedzieć przedsiębiorca?

- URL: https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/
- Rewizja: `content_revision_f4c23cfcd5b6449c83281545b4883e2c`
- Tytuł (WP): BDO – co musi wiedzieć przedsiębiorca?
- Meta title: BDO – rejestracja, ewidencja i sprawozdania
- Meta description: Sprawdź, kogo dotyczy BDO, jak prowadzić ewidencję odpadów, wystawiać KPO, składać sprawozdania i aktualizować dane firmy.
- H1: BDO – co przedsiębiorca musi wiedzieć o rejestracji, ewidencji i sprawozdawczości?
- Lead: Jeśli odpowiadasz w firmie za decyzje środowiskowe, możesz mieć wątpliwości, czy działalność wymaga wpisu do BDO oraz jakie obowiązki dotyczą ewidencji, KPO i sprawozdań. Problem zwykle staje się pilny przed terminem sprawozdawczym, po zmianie danych firmy albo w związku z możliwą kontrolą. Poniższa ścieżka prowadzi od oceny obowiązku rejestracji przez bieżącą obsługę systemu aż po konsekwencje uchybień.

### Sekcje

#### Co to jest BDO i do czego służy przedsiębiorcy?

BDO to Baza danych o produktach i opakowaniach oraz o gospodarce odpadami. System służy między innymi do rejestracji podmiotów, prowadzenia ewidencji odpadów oraz składania sprawozdań.

Dla osoby odpowiedzialnej za decyzje środowiskowe BDO jest miejscem obsługi kilku powiązanych obowiązków firmy. Sam fakt prowadzenia działalności gospodarczej nie rozstrzyga jednak, czy wpis jest wymagany. Decydują zakres działalności, rodzaje produktów lub opakowań oraz sposób gospodarowania odpadami.

#### Kto musi złożyć wniosek o wpis do Rejestru BDO?

Wniosek o wpis składają podmioty objęte obowiązkiem rejestracji ze względu na działalność dotyczącą produktu, opakowania albo gospodarki odpadami. Ocena powinna obejmować rzeczywisty model działania firmy, a nie tylko nazwę działalności lub kod PKD.

Sprawdź, czy firma wprowadza na rynek określone produkty lub produkty w opakowaniach, prowadzi działalność związaną z odpadami albo wytwarza odpady objęte ewidencją. Znaczenie mają również rodzaj i ilość odpadów oraz sposób ich przekazywania.

Jeśli działalność mieści się w zakresie rejestru, wpis powinien poprzedzać czynności objęte tym obowiązkiem. W przypadku kilku miejsc prowadzenia działalności trzeba prawidłowo przypisać zakresy i miejsca w systemie.

#### Kiedy firma może korzystać ze zwolnienia lub wyłączenia z BDO?

Źródło BDO rozróżnia podmioty podlegające wpisowi oraz zwolnienie z wpisu; zakres obowiązku zależy od rodzaju działalności i wskazanych w źródle warunków, dlatego nie każdy podmiot ma identyczny obowiązek rejestracji.

Oficjalne źródło BDO wskazuje, że brak Internetu lub energii nie jest awarią BDO i nie upoważnia do wystawiania papierowych dokumentów ewidencji odpadów po 30 czerwca 2020 r.

#### Jak złożyć wniosek oraz aktualizować dane w Rejestrze BDO?

Wpis do Rejestru-BDO nie następuje automatycznie wraz z założeniem firmy. Przedsiębiorca powinien najpierw ustalić, czy zakres jego działalności, wprowadzane produkty lub opakowania albo sposób gospodarowania odpadami powodują obowiązek rejestracji.

Wniosek powinien odpowiadać rzeczywistemu zakresowi działalności. Jeżeli po uzyskaniu wpisu zmienią się dane firmy lub obszary objęte obowiązkami BDO, konieczna może być aktualizacja wpisu. W praktyce warto regularnie porównywać dane ujawnione w rejestrze z bieżącą działalnością przedsiębiorstwa.

#### Jak prowadzić ewidencję odpadów oraz wystawiać KPO i KPOK?

Gdy dane przekazanie odpadów podlega ewidencji z użyciem Karty Przekazania Odpadów (KPO), kartę sporządza przekazujący posiadacz odpadów przed rozpoczęciem transportu.

Przy określonych operacjach dotyczących odpadów komunalnych stosuje się Kartę Przekazania Odpadów Komunalnych (KPOK). Właściwy rodzaj dokumentu trzeba ustalić osobno dla konkretnego przekazania.

Zgodnie z oficjalnym źródłem BDO Kartę Przekazania Odpadów sporządza przekazujący posiadacz odpadów przed rozpoczęciem transportu, gdy dane przekazanie podlega tej ewidencji.

Oficjalne źródło BDO wyjaśnia, że przy określonych operacjach odpadów komunalnych stosuje się Kartę Przekazania Odpadów Komunalnych (KPOK), a właściwy dokument trzeba ustalić dla konkretnego przekazania.

Oficjalne źródło BDO wskazuje, że brak Internetu lub energii nie jest awarią BDO i nie upoważnia do wystawiania papierowych dokumentów ewidencji odpadów po 30 czerwca 2020 r.

#### Jakie sprawozdania BDO składa przedsiębiorca i do kogo?

Sprawozdawczość BDO obejmuje różne rodzaje sprawozdań, zależnie od działalności przedsiębiorcy. Co do zasady sprawozdanie za poprzedni rok kalendarzowy składa się do 15 marca. Dla wybranych sprawozdań komunalnych termin upływa 31 stycznia.

Właściwość organu może zależeć od siedziby przedsiębiorcy albo miejsca prowadzenia działalności. W określonych przypadkach sprawozdanie należy złożyć do właściwego marszałka województwa.

#### Jak zalogować się do systemu BDO i nadać właściwe uprawnienia?

Do systemu BDO logujesz się przez login.gov.pl, używając dostępnej metody potwierdzenia tożsamości. Po zalogowaniu dostęp do podmiotu zależy od reprezentacji oraz przypisanych kontu uprawnień.

Użytkownik główny zarządza dostępem do podmiotu i może tworzyć konta użytkowników podrzędnych. Użytkownik podrzędny wykonuje tylko czynności wynikające z nadanej roli i przypisanego zakresu.

Przed terminem sprawozdania lub planowanym przekazaniem odpadów sprawdź, czy właściwe osoby widzą odpowiednie miejsca prowadzenia działalności i moduły. Samo skuteczne logowanie nie oznacza jeszcze dostępu do wszystkich funkcji podmiotu.

#### Jakie kary i konsekwencje mogą wynikać z naruszenia obowiązków BDO?

Naruszenia dotyczące Rejestru-BDO mogą skutkować karą aresztu, grzywny albo administracyjną karą pieniężną. Rodzaj i wysokość sankcji zależą od konkretnego naruszenia oraz jego podstawy prawnej.

Za prowadzenie działalności bez wymaganego wpisu może zostać nałożona administracyjna kara pieniężna od 1 000 zł do 1 000 000 zł. Za transport odpadów bez wymaganego wpisu kara może wynieść od 2 000 zł do 10 000 zł.

### FAQ

**Q: BDO – co to jest i kogo dotyczy?**

BDO to Baza danych o produktach i opakowaniach oraz o gospodarce odpadami. Obejmuje podmioty, na które obowiązek rejestracji nakłada zakres działalności związanej między innymi z określonymi produktami, opakowaniami lub odpadami. O wpisie nie przesądza sam fakt prowadzenia firmy.

**Q: Czy każdy przedsiębiorca musi mieć wpis do BDO?**

Nie. Obowiązek zależy od rodzaju działalności, wprowadzanych produktów lub opakowań oraz rodzaju i ilości wytwarzanych albo przetwarzanych odpadów. Firma może korzystać ze zwolnienia lub wyłączenia tylko po spełnieniu warunków właściwych dla jej sytuacji.

**Q: Kto kontroluje BDO i jakie mogą być konsekwencje uchybień?**

Realizację obowiązków mogą sprawdzać właściwe organy w ramach swoich kompetencji, w tym organy ochrony środowiska. Uchybienia mogą prowadzić do wezwania do uzupełnienia danych, odpowiedzialności za wykroczenie albo administracyjnej kary pieniężnej. Rodzaj konsekwencji zależy od konkretnego naruszenia.

### CTA

- Nie masz pewności, czy firma wymaga wpisu, pełnej ewidencji lub konkretnego sprawozdania? Opisz działalność, rodzaje odpadów i obecny status w BDO, aby omówić zakres obowiązków podczas konsultacji.
- Przygotuj numer rejestrowy BDO, zakres działalności, listę odpadów oraz informację o prowadzonych ewidencjach i złożonych sprawozdaniach. Przekaż te dane do weryfikacji obowiązków i ustalenia kolejnych czynności, bez gwarancji określonego wyniku kontroli.

### Decyzja

- `POST /api/content/work-items/.../draft-revisions/content_revision_f4c23cfcd5b6449c83281545b4883e2c/review` z `decision` i `reviewed_by`.

---

## Szkolenia z ochrony środowiska dla firm

- URL: https://www.ekologus.pl/oferta/szkolenia/
- Rewizja: `content_revision_66f7eec3ec9646a5a8ed5327a44e3da8`
- Tytuł (WP): Szkolenia z ochrony środowiska dla firm
- Meta title: Szkolenia z ochrony środowiska dla firm | Ekologus
- Meta description: Wybierz temat i formę szkolenia z ochrony środowiska zgodnie z obowiązkami firmy. Sprawdź zakres szkolenia zamkniętego i poproś o indywidualną wycenę.
- H1: Szkolenia z ochrony środowiska dla firm
- Lead: Odpowiadasz za decyzje środowiskowe w firmie i szukasz szkolenia dopasowanego do jej obowiązków? Zacznij od obszaru, którym zajmują się uczestnicy: emisji, odpadów, wody, sprawozdawczości lub innych zagadnień środowiskowych. Następnie określ potrzebny zakres i formę szkolenia.

### Sekcje

#### Szkolenia z ochrony środowiska dla firm

Szkolenie możesz dobrać do obowiązków środowiskowych firmy i potrzeb osób, które będą w nim uczestniczyć. To praktyczny punkt wyjścia, gdy w organizacji pojawia się potrzeba uporządkowania wiedzy dotyczącej konkretnego obszaru.

Oferta obejmuje różne tematy związane z ochroną środowiska. Dzięki temu nie musisz zaczynać od ogólnego programu. Możesz najpierw wskazać zadania uczestników i zagadnienia, z którymi spotykają się w pracy.

#### Zakres tematów: powietrze, emisje, odpady, woda i pozostałe obowiązki

Zakres szkolenia może dotyczyć jednego obszaru albo kilku powiązanych obowiązków środowiskowych firmy. Dostępna tematyka obejmuje między innymi:

- powietrze, pozwolenia i emisje,
- KOBIZE, opłaty i sprawozdawczość,
- odpady oraz opakowania,
- wodę i ścieki,
- inwestycje i glebę,
- REACH i CLP,
- systemy zarządzania,
- BHP.

Wybierz obszar odpowiadający zadaniom uczestników. Jeśli ich obowiązki łączą kilka tematów, opisz je razem podczas ustalania zakresu.

#### Jak wybrać temat i zakres szkolenia dla firmy

Temat szkolenia wybierz na podstawie rzeczywistych obowiązków organizacji i zadań uczestników. Zacznij od wskazania procesów, dokumentów lub obszarów środowiskowych, którymi zajmuje się zespół.

Następnie określ, które zagadnienia wymagają omówienia. Pomocne będzie przygotowanie krótkiej listy pytań oraz wskazanie, czy uczestnicy potrzebują szkolenia z jednego tematu, czy z kilku powiązanych obszarów.

Przy wyborze zakresu opisz także role uczestników i oczekiwaną formę spotkania. Takie informacje ułatwią dalsze omówienie programu z Ekologus.

#### Indywidualna wycena szkolenia dopasowanego do potrzeb firmy

Wycena szkolenia jest przygotowywana po ustaleniu potrzeb firmy. Przekaż temat, zakres obowiązków uczestników oraz oczekiwaną formę szkolenia.

Opisz również, które zagadnienia mają zostać uwzględnione w programie. Na tej podstawie można omówić zakres szkolenia i przygotować indywidualną wycenę.

#### Szkolenia zamknięte dla jednej organizacji

Szkolenie zamknięte jest przeznaczone dla uczestników z jednej organizacji. Taka forma pozwala ustalić temat i zakres na podstawie potrzeb konkretnej firmy.

Przed rozmową przygotuj informacje o zadaniach uczestników i obszarach, które mają zostać omówione. Wskaż też oczekiwaną formę szkolenia, aby można było doprecyzować propozycję.

#### Usługi rozwojowe związane ze szkoleniami

Zakres rozmowy może obejmować usługi rozwojowe związane ze szkoleniami. Punktem wyjścia pozostają potrzeby uczestników oraz obszar obowiązków środowiskowych firmy.

Przekaż Ekologus informacje o oczekiwanym temacie i formie wsparcia. Pozwoli to ustalić, jaki zakres odpowiada sytuacji organizacji.

#### Następny krok po wybraniu tematu szkolenia

Po wybraniu tematu przygotuj krótki opis sytuacji firmy. Wymień obszary obowiązków, potrzeby uczestników i oczekiwaną formę szkolenia.

Przekaż te informacje Ekologus, aby omówić zakres i indywidualną wycenę. Jeśli nie masz jeszcze gotowej listy tematów, zacznij od opisania zadań zespołu związanych z ochroną środowiska.

### FAQ

**Q: Jak wybrać szkolenie z ochrony środowiska dla firmy?**

Zacznij od obowiązków środowiskowych organizacji i zadań uczestników. Wskaż obszar, którego dotyczy ich praca, na przykład emisje, odpady, wodę lub sprawozdawczość. Następnie określ pytania, oczekiwany zakres i formę szkolenia.

**Q: Czy szkolenia obejmują ochronę środowiska i gospodarkę odpadami?**

Tak. Tematyka obejmuje ochronę środowiska, w tym odpady i opakowania, a także między innymi emisje, wodę, ścieki, opłaty i sprawozdawczość. Zakres szkolenia można omówić na podstawie potrzeb firmy i obowiązków uczestników.

**Q: Jak uzyskać wycenę szkolenia zamkniętego?**

Przekaż Ekologus temat szkolenia, obszar obowiązków firmy, potrzeby uczestników i oczekiwaną formę. Te informacje pozwolą omówić zakres szkolenia zamkniętego i przygotować indywidualną wycenę.

### CTA

- Wiesz już, jakiego szkolenia potrzebuje firma? Opisz obszar obowiązków, poszukiwany zakres i potrzeby uczestników. Przekaż te informacje Ekologus, aby rozpocząć rozmowę o szkoleniu.
- Przygotuj krótką listę tematów, zadań uczestników i oczekiwań dotyczących formy szkolenia. Prześlij ją Ekologus, aby omówić zakres oraz indywidualną wycenę.

### Decyzja

- `POST /api/content/work-items/.../draft-revisions/content_revision_66f7eec3ec9646a5a8ed5327a44e3da8/review` z `decision` i `reviewed_by`.

---

## Doradztwo i outsourcing ekologiczny dla firm

- URL: https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/
- Rewizja: `content_revision_62ef7b61f6fd4a399a41d3ab33094fc9`
- Tytuł (WP): Doradztwo i outsourcing ekologiczny dla firm
- Meta title: Doradztwo ekologiczne i outsourcing ochrony środowiska
- Meta description: Wsparcie firmy w dokumentacji środowiskowej oraz obowiązkach związanych z BDO, KOBiZE, opłatami środowiskowymi, odpadami i opakowaniami.
- H1: Doradztwo i outsourcing ekologiczny dla firm
- Lead: Zmiany przepisów mogą zwiększać zakres dokumentacji i bieżących obowiązków środowiskowych w firmie. Jeśli odpowiadasz za ochronę środowiska i potrzebujesz stałego wsparcia, uporządkujmy aktualne potrzeby firmy oraz zakres wymaganych działań.

### Sekcje

#### Jakie problemy rozwiązuje doradztwo ekologiczne firmy?

Doradztwo ekologiczne pomaga uporządkować obowiązki związane z ochroną środowiska. Obejmuje wsparcie w przygotowaniu dokumentacji oraz w obszarach takich jak BDO, KOBiZE, opłaty środowiskowe, odpady i opakowania.

To rozwiązanie dla firmy, która potrzebuje profesjonalnego wsparcia, ale nie chce samodzielnie koordynować wszystkich tych tematów. Zakres współpracy można odnieść do aktualnej sytuacji firmy i jej bieżących potrzeb.

#### Jak wygląda wsparcie w bieżących obowiązkach ochrony środowiska?

Wsparcie obejmuje bieżące działania związane z dokumentacją środowiskową oraz wskazanymi obszarami obowiązków firmy. Możesz omówić zakres dotyczący BDO, KOBiZE, opłat środowiskowych, odpadów i opakowań.

Outsourcing ekologiczny pozwala przekazać te zadania zewnętrznemu wsparciu. Dzięki temu łatwiej ustalić, które tematy wymagają obsługi i jakiego zakresu pomocy potrzebuje osoba odpowiedzialna za ochronę środowiska w firmie.

#### Czy doradztwo z zakresu ochrony środowiska odpowiada sytuacji Twojej firmy?

Tak, jeśli Twoja firma potrzebuje stałego wsparcia w ochronie środowiska lub chce uporządkować konkretny zakres obowiązków. Dotyczy to między innymi dokumentacji, BDO, KOBiZE, opłat środowiskowych, odpadów i opakowań.

Dobrym momentem na rozmowę jest sytuacja, w której zmiany przepisów zwiększają liczbę zadań albo utrudniają samodzielne prowadzenie dokumentacji. Opisz aktualne obowiązki firmy, aby ustalić, jaki zakres doradztwa lub outsourcingu będzie odpowiedni.

### FAQ

**Q: Czym obejmuje się doradztwo ekologiczne dla firmy?**

Doradztwo ekologiczne obejmuje wsparcie w dokumentacji środowiskowej oraz w obszarach BDO, KOBiZE, opłat środowiskowych, odpadów i opakowań. Zakres można dopasować do aktualnych obowiązków i potrzeb firmy.

**Q: Kiedy firma może potrzebować outsourcingu ochrony środowiska?**

Outsourcing może być potrzebny, gdy firma chce przekazać zewnętrznemu wsparciu bieżące zadania związane z ochroną środowiska. Dotyczy to między innymi dokumentacji, BDO, KOBiZE, opłat środowiskowych, odpadów i opakowań.

**Q: Czy oferta obejmuje wsparcie w obowiązkach środowiskowych przemysłu?**

Oferta obejmuje doradztwo i outsourcing ekologiczny, dokumentację środowiskową oraz wsparcie w obszarach BDO, KOBiZE, opłat środowiskowych, odpadów i opakowań. Odpowiedni zakres pomocy można ustalić na podstawie aktualnej sytuacji firmy.

### CTA

- Opisz aktualne obowiązki i potrzeby środowiskowe swojej firmy. Przekaż informacje o dokumentacji, BDO, KOBiZE, opłatach środowiskowych, odpadach lub opakowaniach, które wymagają wsparcia, aby omówić możliwy zakres doradztwa lub outsourcingu.

### Decyzja

- `POST /api/content/work-items/.../draft-revisions/content_revision_62ef7b61f6fd4a399a41d3ab33094fc9/review` z `decision` i `reviewed_by`.
