# Plany do decyzji Wilka — odczyt live

Data: 18.07.2026  
Źródło: kanoniczny planning API WILQ i lokalny Codex app-server. To jest
readback planów, nie zgoda na publikację ani UAT.

## Co już powstało

| Strona | Usługa | Proposal / run | Wynik |
|---|---|---|---|
| `/bdo-co-musi-wiedziec-przedsiebiorca/` | `ekologus_service_bdo_reporting` | `content_planning_proposal_6a68bd59362641ce90f390b3dfb328c2` / `codex_content_planning_87135135b26d4b58b81f77b4412dac6d` | 8 sekcji, 4 FAQ, 2 CTA, 1 link |
| `/oferta/doradztwo-i-outsourcing-ekologiczny/` | `ekologus_service_environmental_consulting_outsourcing` | `content_planning_proposal_275274ee443c48339785b0e14ec65f86` / `codex_content_planning_3424be8f758a4e89bfc9f2653431edc9` | 5 sekcji, 3 FAQ, 2 CTA, 1 link |

Oba plany są `ready`, mają pełne title/H1/lead/meta, a każde przypisane
zapytanie i evidence pochodzi z aktualnego inputu. Żaden plan nie jest
zatwierdzony i oba mają `publish_ready=false`.

## BDO

**Proponowany tytuł:** BDO – co musi wiedzieć przedsiębiorca?  
**H1:** BDO – co musi wiedzieć przedsiębiorca?

Zakres odpowiada na pytania: czym jest BDO, kto składa wniosek, jakie
dokumenty i karty są potrzebne, papierowa ewidencja, logowanie, przepisy,
obowiązki i konsekwencje. Istniejące sekcje są głównie do przepisania; plan
nie obiecuje zgodności ani uniknięcia kary. Twierdzenia prawne wymagają
aktualnego review Ekologusa.

## Doradztwo i outsourcing

**Proponowany tytuł:** Doradztwo i outsourcing środowiskowy dla firm  
**H1:** Doradztwo środowiskowe i outsourcing dla firm

Zakres odpowiada na sytuacje, w których firma potrzebuje wsparcia, różnicę
między konsultingiem a stałą obsługą, możliwe korzyści i dobór zakresu
współpracy. Istniejące sekcje są oznaczone jako `przepisz`, a brakujące
wyjaśnienia jako `utwórz`; nie ma automatycznego scalania ani obietnic efektu.

## Co trzeba teraz zdecydować

- [ ] Czy zakres i kolejność sekcji BDO odpowiadają realnym pytaniom klientów?
- [ ] Czy zakres i kolejność sekcji doradztwa odpowiada ofercie Ekologusa?
- [ ] Które sekcje zachować, przepisać albo usunąć po review?
- [ ] Czy CTA ma prowadzić do konsultacji / kontaktu i czy jego brzmienie jest właściwe?
- [ ] Które twierdzenia prawne, usługowe lub procesowe wymagają doprecyzowania?

Po tej decyzji API zapisze nowy scope i mapę sekcji. Dopiero wtedy można
uruchomić trwały pełny dokument. Następny dokument nadal będzie
`unreviewed`, a WordPress pozostanie wyłącznie draft-only.

## Uczciwe ograniczenia

- GSC jest użyte do zapytań i metryk strony; nie przedstawiamy go jako pełnej
  listy wszystkich wyszukiwań.
- GA4 i Ahrefs nie mają dokładnego dopasowania do obu stron, więc plan ich nie
  udaje. GA4 ma osobny blocker jakości pomiaru: brak key events/transactions.
- Ads, Merchant, Localo i Social są oznaczone jako nieadekwatne dla tych stron,
  zamiast zasilać plan przypadkowymi danymi.
- Korpus 15 materiałów Ekologusa nadal ma `import_pending`; nie twierdzimy,
  że tekst korzysta już z niezaimportowanych transkrypcji.
- Pełny draft, semantic review, realny human review i WP dry-run pozostają
  kolejnymi krokami.

Szczegóły odczytu konektorów: [LIVE-PROOF.md](./LIVE-PROOF.md).  
Instrukcja oceny operatora: [README-OTWORZ-MNIE.md](./README-OTWORZ-MNIE.md).
