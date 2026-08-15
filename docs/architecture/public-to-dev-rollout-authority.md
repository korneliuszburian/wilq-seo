# Proponowane mapowanie public → dev i odpowiedzialność za rollout pilotów

Rola: `decision record` (ADR). Dokument jest rekomendacją przygotowaną do
decyzji `OWNER`; ma status **PROPOSED / oczekuje na zatwierdzenie**. Nie zapisuje
zatwierdzonej relacji public → dev, nie wskazuje właściciela rolloutu i nie
autoryzuje zapisu na dev, publikacji ani zmiany canonicala. Kod i trwałe rekordy
WILQ pozostają źródłem bieżącego stanu.

## Zakres i stan otwarty

Decyzja dotyczy dwóch pierwszych pilotów:

| Pilot | Dokładny publiczny landing | Relacja public → dev | Właściciel rolloutu |
| --- | --- | --- | --- |
| BDO | `https://www.ekologus.pl/bdo/` | niezatwierdzona; status `unverified` albo `missing` | nierozstrzygnięty |
| Doradztwo i outsourcing ekologiczny | `https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/` | niezatwierdzona; status `unverified` albo `missing` | nierozstrzygnięty |

Globalny profil authoringu WordPress potwierdza wyłącznie możliwości środowiska.
Nie dowodzi, że obiekt o podobnej ścieżce jest odpowiednikiem konkretnego
publicznego landingu. Nie potwierdza też template'u, canonicala ani osoby
uprawnionej do prowadzenia rolloutu.

## Warunek techniczny dla relacji `exact`

Read-only contract może zwrócić `exact` tylko wtedy, gdy dowód relacji wiąże
jednocześnie:

1. dokładny publiczny URL pilota;
2. dokładny zaobserwowany URL dev i `post_id`;
3. identyfikatory dowodów dotyczące właśnie tej relacji.

Odczyt kandydata o tej samej ścieżce bez takiego dowodu ma status `unverified`
i puste `evidence_ids`. Kilku kandydatów również pozostaje `unverified`, bez
samodzielnego wyboru targetu przez WILQ; brak kandydata ma status `missing`.
Sam status `exact` opisuje tożsamość obiektów; nie jest zgodą na zapis ani
publikację.

## Rekomendacja do zatwierdzenia

Rekomendowany domyślny tryb to **potwierdzenie przez OWNER-a osobno dla każdego
pilota przed jakimkolwiek zapisem na dev**. Do czasu tej decyzji WILQ powinien
zachować `unverified` albo `missing`, nie udostępniać targetu jako bieżącego
stanu i nie wyznaczać właściciela rolloutu z globalnych możliwości WordPressa.

## Dowód potrzebny do domknięcia pilotów

### BDO

OWNER powinien zatwierdzić rekord relacji zawierający publiczny URL BDO,
dokładny aktualnie odczytany URL dev, jego `post_id` oraz identyfikatory dowodu,
które pozwalają odtworzyć oba końce relacji. Zmieniony URL, `post_id` albo
niezgodny bieżący odczyt wymaga ponownego potwierdzenia.

### Doradztwo i outsourcing ekologiczny

OWNER powinien zatwierdzić analogiczny, niezależny rekord dla publicznego URL-a
doradztwa i outsourcingu, dokładnego URL-a dev i jego `post_id`, wraz z
identyfikatorami dowodu. Potwierdzenie BDO nie przenosi się na ten pilot.

### Odpowiedzialność za rollout

Osobna decyzja OWNER-a powinna wskazać właściciela rolloutu, piloty i środowisko
objęte jego zakresem oraz granicę uprawnień. Osoba widoczna w review albo w
potwierdzeniu mapowania pól nie staje się przez to właścicielem rolloutu.

## Oczekujące decyzje OWNER-a

- **P1 — relacja BDO:** zatwierdzić albo odrzucić dokładną parę public URL ↔
  dev URL / `post_id` na podstawie wskazanych dowodów.
- **P2 — relacja outsourcingu:** zatwierdzić albo odrzucić jej własną dokładną
  parę public URL ↔ dev URL / `post_id` na podstawie wskazanych dowodów.
- **P3 — odpowiedzialność za rollout:** wskazać właściciela i zakres albo
  jawnie pozostawić rollout bez właściciela i zablokowany.

Do czasu rozstrzygnięcia P1–P3 żadna relacja ani odpowiedzialność za rollout nie
jest uznana za zdecydowaną.
