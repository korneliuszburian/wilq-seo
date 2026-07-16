# 3. Tekst, review i przekazanie

## Co ma znaleźć się w pełnym dokumencie

Jedna niezmienna rewizja obejmuje wszystkie assety strony:

- tytuł WordPress, meta title, meta description, H1 i lead;
- sekcje ze stabilnymi ID, body, query, evidence i claims;
- FAQ z odpowiedziami i lineage;
- bloki CTA;
- linki wewnętrzne wraz z miejscem użycia;
- digests planu, wejścia, usługi i inventory;
- digest całego dokumentu.

Zmiana dowolnego assetu tworzy nową rewizję i unieważnia review starego digestu.

## Trzy niezależne poziomy jakości

1. **Bramki deterministyczne** sprawdzają lineage, aktualny digest, kompletność,
   claims, duplikację, długości pól, CTA, linki i bezpieczeństwo.
2. **Advisory semantic review** ocenia dokładnie zapisaną rewizję według
   wersjonowanych kryteriów. Zapisuje findings i `codex_run_id`, ale nie
   zatwierdza własnego tekstu.
3. **Review człowieka** należy do SEO reviewera, content editora i marketera.
   Tylko ludzie mogą zatwierdzić exact revision i przyznać 10/10.

Finding nie uruchamia samonaprawiania. Człowiek wybiera sekcje, a poprawka
tworzy child revision; nie nadpisuje historii.

## Stan bieżący

Pełny draft dla realnego BDO i outsourcingu nie został jeszcze wygenerowany.
To prawidłowa blokada, ponieważ obie karty usług wymagają owner review. Paczka
nie pokazuje placeholdera jako tekstu gotowego do oceny.

Po odblokowaniu w tym katalogu muszą pojawić się osobno dla obu case'ów:

- decyzja i exact źródła;
- baseline metryk;
- plan oraz mapa query → section;
- pełny dokument i page preview;
- meta, FAQ, CTA i linkowanie;
- deterministic i semantic findings;
- diff między rewizjami;
- WordPress dry-run;
- trzy podpisane formularze oceny.

## Przekazanie do WordPressa

WILQ przygotowuje revision-bound `ActionObject`. WordPress może utworzyć
wyłącznie nowy szkic na devie po osobnym potwierdzeniu. Publikacja, aktualizacja
istniejącej strony i automatyczny zapis meta bez potwierdzonego mapowania
pozostają niedostępne.

Dry-run musi pokazać pełne body oraz wszystkie page assets. Jeśli profil
WordPress/ACF nie ma dokładnego mapowania meta, pola pozostają widoczne w paczce
z typed blockerem — nie wolno ich zgubić.

## Po publikacji przez ownera

Pipeline używa istniejącego kontraktu publication-bound: baseline → observation
window → exact metryki z lineage → learning proposal do review. Nie wymyśla
targetów, nie ogłasza sukcesu na podstawie jednego odczytu i nie uruchamia
drugiego measurement loopu.
