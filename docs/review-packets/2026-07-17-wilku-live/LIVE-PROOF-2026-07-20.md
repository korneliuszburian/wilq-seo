# WILQ — aktualny live readback dla marketera

**Odczyt:** 20 lipca 2026, WILQ API `127.0.0.1:8000`  
**Dashboard:** `http://127.0.0.1:5173/content-workflow`

To jest aktualny odczyt API, a nie deklaracja ukończenia produktu. Nie zawiera
sekretów ani surowych odpowiedzi vendorów.

## Co WILQ widzi teraz

- 12 dostępnych konektorów; 9 skonfigurowanych do odczytu, 2 mają brakujące
  credentials, a Codex Runtime nie jest źródłem metryk marketingowych.
- 23 source-backed karty wiedzy i 34 podsumowania dowodów w context packu.
- 50 potwierdzonych stron WordPress w bieżącym content diagnostics.
- 51 decyzji contentowych; główne źródła tego widoku to WordPress, GSC i Ahrefs.
- GSC, GA4, Ads, Ahrefs, Merchant, Localo i WordPress raportują świeży odczyt
  w bieżącym context packu. Stan świeżości jest sprawdzany przy każdym odczycie.

## Dwa kontrolne adresy

### BDO

`https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/`

- decyzja: **odświeżyć**, status `review_required`;
- 13 zapytań z GSC, główne: `bdo co to`;
- evidence: GSC `ev_refresh_refresh_google_search_console_6b327eea1659`,
  WordPress `ev_refresh_refresh_wordpress_ekologus_ff4e784ddded`;
- źródła użyte dla tej decyzji: GSC + WordPress;
- blokady claims: obietnica do sprawdzenia, wpływ na przychód;
- następny krok: sprawdzić ryzykowne twierdzenia i dopiero przygotować plan.

### Doradztwo i outsourcing ekologiczny

`https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/`

- decyzja: **odświeżyć**, status `review_required`;
- 20 zapytań z GSC, główne: `doradztwo ochrona środowiska`;
- evidence: GSC `ev_refresh_refresh_google_search_console_6b327eea1659`,
  WordPress `ev_refresh_refresh_wordpress_ekologus_ff4e784ddded`;
- źródła użyte dla tej decyzji: GSC + WordPress;
- blokady claims: obietnica do sprawdzenia, wpływ na przychód;
- następny krok: sprawdzić ryzykowne twierdzenia i dopiero przygotować plan.

## Jak powstaje mapa sekcji

Mapa nie jest wybierana ręcznie i nie jest zaszyta dla BDO ani outsourcingu.
Resolver czyta wybrany adres z inventory WordPress. Jeżeli dostępne są
sekcje ACF, wykorzystuje ich nagłówki; jeżeli nie, bierze nagłówki z
`the_content`/publicznego HTML. Następnie łączy je z usługą, zapytaniami,
evidence i ograniczeniami claims. Brak rozpoznawalnej struktury pozostaje
typed blockerem — system nie wymyśla sekcji.

## Czego ten odczyt nie dowodzi

- nie dowodzi wzrostu CTR, leadów, konwersji ani przychodu;
- nie dowodzi zatwierdzenia kart usług ani jakości finalnego tekstu;
- nie dowodzi pełnej kompletności GSC (część zapytań może być pominięta);
- nie uruchamia publikacji ani zapisu do WordPress;
- pełny draft i semantic review pozostają zależne od zatwierdzeń oraz aktywacji
  storage semantic-review w autoryzowanym maintenance window.

## Co marketer ma zrobić

1. Otworzyć jeden z dwóch adresów albo wybrać dowolną stronę z inventory.
2. Sprawdzić realne metryki, materiał WordPress i status źródeł.
3. Ocenić plan oraz blokady claims; nie akceptować automatycznie żadnej
   publikacji.
4. Odesłać formularz oceny z uwagami o decyzji, mięsie na pierwszym ekranie i
   brakujących materiałach Ekologusa.
