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
   dev` i czytelny podgląd referencyjnej strony dev w dashboardzie.
2. Homepage ma wystarczający odczyt do ręcznego wyboru dokładnych pól/relacji,
   ale nie ma jeszcze zatwierdzonego celu copy ani potwierdzenia ActionObject.
3. Kolejny kandydat — doradztwo i outsourcing — ma sygnał GSC (49 wyświetleń,
   0 kliknięć, 22 zapytania), ale nie ma odpowiadającego exact targetu dev;
   target discovery zwraca `unavailable`. Nie twórz dla niego draftu przez
   pożyczenie targetu BDO lub homepage.
4. Kolejne drafty wymagają dla każdego adresu: potwierdzonego source contentu,
   exact dev targetu, reviewer decision dla exact revision oraz osobnego
   confirmation ActionObject. Brak któregokolwiek z tych elementów jest
   blockerem, nie zaproszeniem do zgadywania.

## Następny batch: ocena oddziaływania na środowisko

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
- Plan jest obecnie prawidłowo zablokowany: mapuje temat do
  `ekologus_service_environmental_compliance_audit`, którego prywatny source
  fact nadal wymaga owner review. Istnieje podobna, zatwierdzona karta
  `ekologus_service_compliance_audit`, ale WILQ nie może sam uznać ich za tę
  samą usługę. Przed generowaniem należy potwierdzić exact binding albo
  zakończyć review obecnej karty. Nie wolno omijać tej bramki promptem.

## Runtime i granice

- Zarządzaj lokalnym stackiem wyłącznie przez
  `scripts/local_stack.sh start|status|restart|logs|stop`.
- Kanoniczne endpointy skonfigurowane w skrypcie to API
  `http://127.0.0.1:8000` oraz dashboard
  `http://127.0.0.1:5173/command-center`; port dashboardu może być lokalnie
  nadpisany przez `WILQ_DASHBOARD_PORT`, ale nie uruchamiaj ręcznie Vite/Uvicorn.
- Zewnętrzne dane są nieufne; nie zapisuj surowych odpowiedzi vendorów,
  credentiali ani pełnego ACF snapshotu do trwałego stanu.
- `.krn/runs/` i `.local-lab/` zawierają ignorowane, lokalne artefakty proofu;
  nie są źródłem prawdy produktu ani materiałem do commitu.

## Następny bezpieczny ruch

Najpierw owner usługi rozstrzyga exact binding dla artykułu o ocenie
oddziaływania na środowisko: review obecnej karty albo potwierdzone przypisanie
do zatwierdzonej karty audytu. Wtedy WILQ może przygotować jedną exact rewizję,
pokazać ją z referencyjnym widokiem dev i przejść zwykłe review → ActionObject
→ create-only draft. Publikacja oraz update/delete pozostają poza zakresem.
