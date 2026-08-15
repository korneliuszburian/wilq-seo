# Wdrożenie przez systemd

Pliki `wilq-api.service` i `wilq-dashboard.service` są szablonami. Właściciel
wdrożenia musi wybrać konto systemowe, grupę oraz rzeczywiste ścieżki, zastąpić
wartości `wilku`, `/opt/wilq` i `/home/wilku/.local/bin`, a także utworzyć
katalogi stanu i kopii z prawem zapisu dla tego konta. Ścieżki ustawione przez
`WILQ_STATE_DB` i `WILQ_METRIC_DB` muszą mieścić się w `ReadWritePaths` albo ta
lista musi zostać świadomie dopasowana. Nie wpisuj sekretów do jednostek;
przechowuj je w chronionym pliku `.env` wskazanym przez `EnvironmentFile` albo
w środowisku usługi.

## Instalacja API

1. Skopiuj szablon i uzupełnij wartości wdrożeniowe:

   ```bash
   sudo cp deploy/wilq-api.service /etc/systemd/system/wilq-api.service
   sudoedit /etc/systemd/system/wilq-api.service
   systemd-analyze verify /etc/systemd/system/wilq-api.service
   ```

2. Przeładuj konfigurację i uruchom usługę:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now wilq-api
   ```

Przed startem przygotuj środowisko zależności, ponieważ jednostka ustawia
`UV_NO_SYNC=1` i podczas pracy nie zapisuje w repozytorium ani w cache `uv`.
`WILQ_API_RELOAD` musi mieć wartość `0` w produkcji. Wartości z
`EnvironmentFile` mają pierwszeństwo przed `Environment=`, dlatego `.env` nie
może nadpisać tego ustawienia inną wartością. Scheduler pozostaje wyłączony,
dopóki chroniony plik środowiskowy nie ustawi jawnie
`WILQ_ENABLE_SCHEDULER=1`.

Preferowana obsługa panelu nie wymaga drugiego procesu: zbuduj SPA i dodaj do
środowiska jednostki API `WILQ_SERVE_DASHBOARD=1` oraz właściwą bezwzględną
ścieżkę `WILQ_DASHBOARD_DIST`. `wilq-dashboard.service` jest tylko alternatywną,
osobno nazwaną jednostką tego samego procesu FastAPI. Używaj jej zamiast, a nie
równolegle z `wilq-api.service`, bo obie nasłuchują na porcie `8000` i deklarują
wzajemny konflikt. Dla jednostki alternatywnej `.env` nie może nadpisywać
`WILQ_SERVE_DASHBOARD=1` ani wskazanej ścieżki dystrybucji innymi wartościami.

## Próba restartu po awarii

Wykonaj dowód na docelowym hoście po instalacji (poniższe polecenia umyślnie
zabijają proces API):

```bash
sudo systemctl restart wilq-api
systemctl is-active --quiet wilq-api || exit 1
systemctl is-active wilq-api
old_pid="$(systemctl show --property MainPID --value wilq-api)"
if [[ ! "$old_pid" =~ ^[0-9]+$ ]] || (( old_pid <= 1 )); then
  echo "Nieprawidłowy MainPID: $old_pid" >&2
  exit 1
fi
# Bezpieczny, ograniczony do jednostki odpowiednik: kill -9 <pid>
sudo systemctl kill --kill-whom=main --signal=KILL wilq-api
for _ in {1..10}; do
  systemctl is-active --quiet wilq-api && \
    curl -fsS http://127.0.0.1:8000/api/health >/dev/null && break
  sleep 1
done
systemctl is-active --quiet wilq-api || exit 1
curl -fsS http://127.0.0.1:8000/api/health >/dev/null || exit 1
systemctl is-active wilq-api
new_pid="$(systemctl show --property MainPID --value wilq-api)"
if [[ ! "$new_pid" =~ ^[0-9]+$ ]] || (( new_pid <= 1 || new_pid == old_pid )); then
  echo "Proces nie otrzymał nowego MainPID: $new_pid" >&2
  exit 1
fi
systemctl status --no-pager wilq-api
curl -fsS http://127.0.0.1:8000/api/health
journalctl -u wilq-api -n 50 --no-pager
```

Oczekiwany wynik to ponownie aktywna usługa, nowy PID i poprawna odpowiedź
`/api/health`. Zachowaj wynik `status`, `curl` i dziennika jako dowód z hosta;
sam szablon nie jest dowodem wykonania próby awarii.
