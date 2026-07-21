# Second opinion — pierwszy viewport Treści i SEO

To jest nowy, oczyszczony pakiet do zewnętrznego review. Zastępuje wcześniejsze
artefakty z tego folderu; nie należy ich traktować jako aktualnego stanu.

Fixed point kodu: `9e09fd13` (`feat(content): author revisions as html`).
Ten fixed point domknął poprzedni slice: canonical `content_html` w warsztacie,
podglądzie i exact revision. Ten review dotyczy wyłącznie następnego slice’a:
orientacji marketera w pierwszym viewporcie `/content-workflow`.

## Materiał

| Plik | Viewport | Co pokazuje |
| --- | ---: | --- |
| `bdo-current-desktop-first-viewport.png` | 1440×900 | aktualny, załadowany widok BDO bez przewijania |
| `bdo-current-desktop-sources-open.png` | 1440×900 | techniczne szczegóły po jawnym otwarciu „Źródła i szczegóły” |
| `bdo-current-mobile-first-viewport.png` | 390×844 | aktualny pierwszy viewport na iPhone 14 |

To celowo tylko trzy kadry potrzebne do oceny pierwszego viewporu: desktop,
mobile i źródła otwarte na żądanie. Pełne, przewijane kadry nie są częścią
pakietu, bo nie odpowiadają na pytania tego review. Wszystkie obrazy pochodzą
z lokalnego, załadowanego dashboardu, nie z mockupu.
Zostały obejrzane po zapisie. Mobile nie ma poziomego overflow (`390px ==
scrollWidth 390px`).

## Stan API użyty w kadrach

- Strona: `BDO - CO MUSI WIEDZIEĆ PRZEDSIĘBIORCA? - Ekologus`
- URL: `https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/`
- Usługa: `ekologus_service_bdo_reporting`
- Rekomendacja: odświeżenie istniejącej treści.
- GSC: 181 wyświetleń, 0 kliknięć, CTR 0%; pojedynczy częściowy odczyt, bez
  porównywalnego okresu — nie jest trendem.
- GA4: brak exact danych dla strony.
- Revision: `content_revision_93416d2571264f31b7f8ae8621ada769`, nieaktualna
  względem bieżącego kontekstu; bieżący scope wymaga review.

Podczas zrobienia kadr otwarto i zamknięto jedynie „Źródła i szczegóły”. Log
sieci po wyczyszczeniu zawiera wyłącznie odczyt `GET /enrichment`; nie ma POST
do rewizji, generowania, review, handoffu ani WordPressa.

Pełne zlecenie dla reviewera: [`prompt.md`](prompt.md).
