# Proponowany cel środowiska produkcyjnego oraz auth/TLS

Rola: `decision record` (ADR). Dokument jest rekomendacją przygotowaną do
decyzji `OWNER`; ma status **proposed / oczekuje na zatwierdzenie**. Nie zapisuje
decyzji właściciela, nie autoryzuje deployu ani zmian w kodzie.

## Opcje

| Opcja | Charakterystyka i koszt | Co domyka po zatwierdzeniu przez OWNER-a | Co pozostaje otwarte | Główne ryzyko |
| --- | --- | --- | --- | --- |
| **A. Lokalny pilot na komputerze operatora** | API pozostaje loopback-only; zdalne auth i TLS nie są potrzebne. Najtańsza opcja, zgodna z obecnym stanem. | Wybór celu domyka decyzję L9. Jawne przyjęcie loopback-only domyka decyzję L1, a brak TLS na loopbacku — decyzję L2. L3 domyka się tylko razem z osobną decyzją, że pilot jest single-user. | Zdalny dostęp oraz dowód deployu, restartu i alertu na wybranym komputerze. | Każdy lokalny proces ma dostęp do API, a dostępność zależy od komputera operatora. |
| **B. Serwer self-hosted w LAN / domu** | Usługa jest always-on, ale wymaga reverse proxy, TLS i auth. Trzeba też wybrać miejsce Codex login. | Wybór celu domyka decyzję L9 i określa wymagany kształt L1/L2; nie zamyka ich bez implementacji i dowodu. L3 wymaga decyzji single-user albo zweryfikowanego kontraktu actora. | Model auth, terminacja TLS, tożsamość actora, miejsce Codexa oraz próby na serwerze. | LAN nie jest granicą zaufania; błędna konfiguracja proxy może odsłonić API lub poświadczenia. |
| **C. Cloud VPS z publicznym HTTPS** | Zapewnia zdalny dostęp. Pełne auth i TLS są wymagane od pierwszego dnia; sekrety są na serwerze, backup jest off-box, a Codex login na serwerze wymaga osobnej decyzji. | Wybór celu domyka decyzję L9. L1/L2 domykają się dopiero po wdrożeniu i sprawdzeniu auth oraz TLS; L3 pozostaje osobną decyzją. | Kontrakt actora, utrzymanie hosta, kanał alarmowy, off-box restore oraz umiejscowienie Codexa. | Największa powierzchnia ataku i koszt operacyjny przy publicznym dostępie oraz poświadczeniach na serwerze. |

„Domyka” oznacza tu domknięcie wskazanej **decyzji**, nie produkcyjną
weryfikację. Deploy, awaria testowa, alert i restore na wybranym hoście nadal
muszą dostarczyć oddzielny dowód operacyjny.

## Ukryta zależność: loopback API i Codex login

Seam Codex app-server w `wilq/codex/app_server.py` korzysta z istniejącego
lokalnego `codex login` (`auth.json`) i przekazuje jego odizolowaną kopię do
procesu app-server. Dla B/C `OWNER` musi rozstrzygnąć, czy Codex pozostaje na
komputerze operatora, czy serwer otrzymuje własny login. Loopbackowa brama API
i ten seam są sprzężone: miejsce procesu Codexa wyznacza, czy może on dotrzeć
do loopback-only API bez otwierania nowej zdalnej ścieżki dostępu.

## Rekomendacja do zatwierdzenia

Rekomendowana jest **A. lokalny pilot** jako najniższe ryzyko następnego kroku.
**B** ma sens dopiero, gdy Wilku musi pracować z innego komputera i `OWNER`
zaakceptuje dodatkowe auth, TLS oraz utrzymanie. **C nie jest teraz
rekomendowana**: publiczny VPS zwiększa ryzyko i zakres operacyjny bez
potwierdzonej potrzeby pilota.

## Oczekujące decyzje OWNER-a

- **P1 — środowisko docelowe:** A, B albo C.
- **P2 — model auth:** loopback-only albo key/OAuth przez `oauth2-proxy`.
- **P3 — TLS:** brak TLS na loopbacku albo terminacja przez Caddy.
- **P4 — actor:** czy pilot pozostaje single-user, co domyka decyzję L3, czy
  wymaga zweryfikowanego kontraktu actora.

Każda pozycja jest decyzją `OWNER`. Do czasu ich wyboru nie należy wprowadzać
wynikających z nich zmian w kodzie ani wykonywać deployu.
