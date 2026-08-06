# Current Delivery State — 2026-08-06

Przeczytaj przed zmianą Content Ops, dashboardu `/content-workflow`, kontraktu
ACF albo dev-draft delivery. Git i Beads zachowują historię zakończonych
slice’ów; ten dokument opisuje wyłącznie bieżący stan operacyjny.

## Decyzja na dziś

WILQ ma jeden API-owned workflow dla treści:

```text
wybór istniejącej strony albo briefu nowej
→ planning i immutable revision
→ semantic + human review
→ dokładne mapowanie do dev
→ ActionObject
→ wyłącznie nowy draft na dev
```

Nie ma ścieżki bezpośredniego publish, update ani delete WordPress. Każdy zapis
na dev pozostaje oddzielną decyzją człowieka, związany z exact revision,
targetem oraz mappingiem. Dashboard i operator skills używają WILQ API;
browser nie wywołuje Codexa ani adaptera WordPress bezpośrednio.

## Potwierdzony pilot BDO

- Publiczny work item:
  `content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`.
- Dev target: istniejący WordPress post `1353`, używający bezpośrednio
  `wordpress_post_content`, a nie ACF.
- Po pełnym łańcuchu ActionObject utworzono wyłącznie nowy post dev `1932` ze
  statusem `draft`. Źródłowy post `1353` i wcześniejszy wadliwy szkic `1931`
  nie zostały zaktualizowane, opublikowane ani usunięte.
- Odczyt po zapisie potwierdza podgląd szkicu:
  `https://ekologus.dev.proudsite.pl/?p=1932`.
- Akcja:
  `act_content_dev_draft_a75ad8a27e9e4f07b773205fdf0a5b7f`; exact revision:
  `content_revision_56bfb0e0fe1742738dfe3f07a39f780c`.
- Treść szkicu nie zawiera powielonego H1 w `post_content`; jeden H1 pozostaje
  tytułem WordPressa. Problem wizualnej hierarchii H1/H2 należy do motywu
  `ekologus-2025`; wskazówki są w `notes.md`.
- BDO jest gotowe do read-only UAT i oddzielnego review człowieka. Nie jest
  publikacją ani automatyczną zgodą prawną.

## Ostatnia weryfikacja techniczna

- CI dla fixed pointu `0e314a86` przeszła w całości: Python quality/security
  (w tym 1525 izolowanych testów), frontend lint/typecheck/test oraz
  `scripts/verify.sh` z integracją i E2E. Pełna bramka jest uruchamiana w CI;
  lokalny pełny suite wymaga jawnego, ekskluzywnego okna i nie działa na
  współdzielonej maszynie.
- CI dla `195bec2d` również przeszła w całości: Python quality/security,
  frontend lint/typecheck/test oraz `scripts/verify.sh`. Naprawa wiąże cache
  measurement evidence z trwałą bazą metryk i nie cache'uje odczytu bez
  persisted refresh lineage; dzięki temu nowy fakt nie może przez TTL udawać
  starszego snapshotu.
- Bieżący odczyt WILQ API nadal wskazuje exact revision
  `content_revision_56bfb0e0fe1742738dfe3f07a39f780c` jako zatwierdzony
  dokument BDO o digescie
  `3c14b3d8a71e77a4d561ce2ce5b5df47c84b99e960a6c5d56d83f59ad738ceec`.
- ActionObject `act_content_dev_draft_a75ad8a27e9e4f07b773205fdf0a5b7f`
  pozostaje wykonanym, jednorazowym create-only przygotowaniem szkicu. Jego
  ponowny apply jest zablokowany; odczyt nie tworzy nowej akcji ani nie zmienia
  WordPressa.
- Dashboard nie emituje już ostrzeżenia React o zduplikowanych kluczach, gdy
  metryka Localo ma dwa różne wymiary z tą samą etykietą dla marketera.

## Strona główna i ACF na dev

- Homepage work item:
  `content_work_item_inventory_c90528e2454d9f3de03d2394`, decyzja
  `refresh_or_merge` dla `https://www.ekologus.pl/`.
- Bieżący sygnał GSC jest częściowy: 43 wyświetlenia, 1 kliknięcie, CTR 2,33%
  i 25 zapytań; dowody to
  `ev_refresh_refresh_google_search_console_85a41668ed19` oraz
  `ev_refresh_refresh_wordpress_ekologus_1e5cfcd8d131`. GA4 jest
  settling/unverified, a Ahrefs unverified — nie wolno na ich podstawie
  twierdzić o jakości leadów, konwersjach lub przychodzie.
- Dev target to WordPress page `2`, root ACF `flexible-home`, z 9 obserwowanymi
  layoutami. OPTIONS oraz bieżący snapshot źródła są obowiązkowe przy każdym
  mapowaniu i apply.
- Preserve-first profil pozwala dziś tylko na bezpośrednie pola tekstowe
  `heading` oraz `slider_text` w layoutcie Services #2. Wszystkie pozostałe
  wartości są klonowane z aktualnego źródła i nie są konstruowane przez WILQ.
- Relacja `services_order` została odczytana jako dokładna lista ID i
  potwierdzona przez publiczny render dev: EKOdokumentacje, EKOdoradztwo,
  EKOprzegląd, Obsługa i Bezpieczeństwo Zakładu, Zrównoważony rozwój, Szkolenia
  i rozwój oraz Sprzedaż sorbentów. To obserwacja w target-discovery/UI, nie
  write profile i nie zgoda na zmianę kolejności albo usunięcie karty.
- Deklarowany kierunek produktu mówi, że główna strona nie ma obsługiwać sklepu
  ani sorbentów. Zanim powstanie ActionObject, człowiek musi potwierdzić
  dokładną zmianę (np. usunięcie ID `352`) i oczekiwany wynik dla strony dev.

## Co realnie jest gotowe, a co blokuje skalowanie

1. BDO ma pełny, bezpieczny przykład `revision → ActionObject → nowy draft
   dev` i czytelny podgląd referencyjnej strony dev w dashboardzie. Exact
   ActionObject pozostaje jednorazowy; nie twórz drugiego szkicu dla tej samej
   rewizji.
2. KIP ma drugi, niezależny przykład tej samej create-only ścieżki: revision
   `content_revision_b19dcd1c79ae4a6abb00777b3ad795dc`, semantic review
   `content_semantic_review_838b74b63266491eb86d892f2f28b245`, confirmation
   `content_target_mapping_confirmation_b0450c25dddc484cae73510776eff8c1` i
   ActionObject `act_content_dev_draft_784fe5fc639049e0aa8f127722af7ee4`.
   Powstał wyłącznie nowy draft dev `1934`; referencyjny post `1294` pozostał
   opublikowany i niezmieniony. Odczyt po zapisie potwierdza podgląd szkicu:
   `https://ekologus.dev.proudsite.pl/?p=1934`.
3. Homepage ma wystarczający odczyt do ręcznego wyboru dokładnych pól/relacji,
   ale nie ma jeszcze zatwierdzonego celu copy ani potwierdzenia ActionObject.
4. Doradztwo i outsourcing ma poprawioną, zatwierdzoną rewizję
   `content_revision_6a8fa15ce0d342388fb54d6cb0f55a4c` (digest
   `9447171…0a3a`) oraz review `content_semantic_review_463c834ca22847d383382387da5304fc`
   z 9/9 silnymi wymiarami i bez findings. Semantic repair usunął
   niepotwierdzone przypisanie lokalnej frazy „Warszawa”. Delivery jest jednak
   zablokowane: target discovery zwraca `unavailable`, bo dev nie zawiera
   obiektu pod dokładnym adresem usługi. Nie twórz dla niego draftu przez
   pożyczenie targetu BDO, KIP lub homepage.
5. Kolejne drafty wymagają dla każdego adresu: potwierdzonego source contentu,
   exact dev targetu, reviewer decision dla exact revision oraz osobnego
   confirmation ActionObject. Brak któregokolwiek z tych elementów jest
   blockerem, nie zaproszeniem do zgadywania.

## Dostarczony batch: ocena oddziaływania na środowisko

- Wybrany kandydat:
  `content_work_item_content_decision_https___www_ekologus_pl_ocena_wplywu_projektow_na_srodowisko`.
  To istniejący, editorial-eligible URL z publicznym source contentem,
  sygnałem GSC `45` wyświetleń / `0` kliknięć / `21` zapytań w częściowym oknie
  oraz dowodami WordPress i GSC.
- Dev discovery znalazł exact target: post `1314`,
  `https://ekologus.dev.proudsite.pl/ocena-wplywu-projektow-na-srodowisko/`.
  Używa natywnego `wordpress_post_content`; profil zapisu to `not_required`
  dla ACF, więc ewentualny draft może korzystać z tej samej create-only granicy
  co BDO.
- Discovery odrzuca obecnie tylko rzeczywiście różne obiekty. Powielona,
  identyczna obserwacja posta `1314` była fałszywą niejednoznacznością i została
  scalona w `7db9c291`; zgodność URL-a nadal nie jest mapowaniem ani zgodą na
  zapis.
- Owner review exact propozycji „Audyt zgodności środowiskowej” został
  odnotowany przez append-only lokalną projekcję. WILQ użył wyłącznie
  zsanityzowanego reviewed-internal lineage; nie przypiął podobnej karty ani
  nie ujawnił prywatnego źródła.
- Exact plan `content_planning_proposal_171e5c84eb9d4c61a2c1bea66f95c1a6`,
  revision `content_revision_fefc92d17dca4d5eaad590c3104eb260` i semantic
  review `content_semantic_review_791f6a7b2e404cd0b633fd7670f12077` przeszły
  9/9 silnych wymiarów bez findings. ActionObject utworzył wyłącznie draft
  dev `1933`; referencyjny post `1314` nie został zmieniony. Odczyt po
  zapisie potwierdza podgląd szkicu:
  `https://ekologus.dev.proudsite.pl/?p=1933`.
- Preflight „Europejskiego Zielonego Ładu” potwierdza, że post dev `1332`
  ma bezpośredni kontrakt `wordpress_post_content`, ale plan także blokuje
  review-required karta `ekologus_service_environmental_compliance`. Nie
  zastępuje to przeglądu exact karty dla „Oceny…”.

## Runtime i granice

- Zarządzaj lokalnym stackiem wyłącznie przez
  `scripts/local_stack.sh start|status|restart|logs|stop`.
- Kanoniczne endpointy skonfigurowane w skrypcie to API
  `http://127.0.0.1:8000` oraz dashboard
  `http://127.0.0.1:5173/command-center`; port dashboardu może być lokalnie
  nadpisany przez `WILQ_DASHBOARD_PORT`, ale nie uruchamiaj ręcznie Vite/Uvicorn.
  Manager zapisuje port faktycznie uruchomionego własnego procesu w prywatnym
  runtime state, więc późniejsze `status` i `stop` nie mylą go z domyślnym
  portem zajętym przez inny checkout.
- Zewnętrzne dane są nieufne; nie zapisuj surowych odpowiedzi vendorów,
  credentiali ani pełnego ACF snapshotu do trwałego stanu.
- `.krn/runs/` i `.local-lab/` zawierają ignorowane, lokalne artefakty proofu;
  nie są źródłem prawdy produktu ani materiałem do commitu.

## Następny bezpieczny ruch

Provisionuj lub wskaż rzeczywisty obiekt dev dla dokładnego adresu Doradztwa i
outsourcingu. Musi to być właściwa strona usługi oraz odczytywalny target ACF,
nie podobny artykuł lub zastępczy post. Dopiero wtedy WILQ ponownie odczyta
target, pokaże preserve-first mapping, poprosi o jego osobne potwierdzenie i
utworzy najwyżej jeden nowy draft dev. Publikacja oraz update/delete pozostają
poza zakresem.
