# Lokalny monitoring dostępności WILQ

`scripts/health_check.sh` jest prostym hakiem obserwacyjnym dla procesu API.
Domyślnie odpytuje `http://127.0.0.1:8000`; inny adres ustaw przez
`WILQ_HEALTH_BASE_URL`. Nie umieszczaj danych dostępowych w bazowym URL.

Próg pojedynczej próby jest celowo prosty: błąd połączenia, `health.status`
inny niż `ok` albo odpowiedź `/api/system/status` inna niż HTTP 200 kończy
skrypt niezerowym kodem. Każdy request ma limit 10 sekund.

## Cron co minutę

Ogólny wpis ma postać:

```cron
* * * * * /path/to/scripts/health_check.sh || /path/to/notify
```

Przykład na tym samym hoście co loopback API zapisuje porażkę do dziennika
systemowego. Zastąp `/opt/wilq` rzeczywistą ścieżką wdrożenia:

```cron
* * * * * WILQ_HEALTH_BASE_URL=http://127.0.0.1:8000 /opt/wilq/scripts/health_check.sh >/dev/null 2>&1 || /usr/bin/logger -p user.err -t wilq-healthcheck "WILQ: kontrola API nie powiodła się"
```

`logger` daje lokalny sygnał, ale sam nie gwarantuje powiadomienia człowieka.
W docelowym środowisku podłącz wybrany kanał do tych wpisów albo zastąp
`logger` zatwierdzonym programem powiadamiającym.

## Timer systemd zamiast crona

Utwórz `/etc/systemd/system/wilq-healthcheck.service` (konto i ścieżka są
wartościami wdrożeniowymi):

```ini
[Unit]
Description=Kontrola dostępności WILQ API
After=wilq-api.service

[Service]
Type=oneshot
User=wilku
WorkingDirectory=/opt/wilq
Environment=WILQ_HEALTH_BASE_URL=http://127.0.0.1:8000
ExecStart=/opt/wilq/scripts/health_check.sh
NoNewPrivileges=true
PrivateTmp=true
```

Następnie utwórz `/etc/systemd/system/wilq-healthcheck.timer`:

```ini
[Unit]
Description=Uruchamiaj kontrolę WILQ co minutę

[Timer]
OnCalendar=*-*-* *:*:00
AccuracySec=1s
Persistent=true
Unit=wilq-healthcheck.service

[Install]
WantedBy=timers.target
```

Włącz timer i sprawdź ostatni wynik:

```bash
sudo systemd-analyze verify \
  /etc/systemd/system/wilq-healthcheck.service \
  /etc/systemd/system/wilq-healthcheck.timer
sudo systemctl daemon-reload
sudo systemctl enable --now wilq-healthcheck.timer
sudo systemctl start wilq-healthcheck.service
systemctl show wilq-healthcheck.service --property=Result --property=ExecMainStatus
journalctl -u wilq-healthcheck.service -n 20 --no-pager
```

Nie dodawaj `RemainAfterExit=true`: usługa ma zakończyć się po każdej próbie,
aby timer mógł uruchomić następną.

## Znaczenie endpointów i reakcja

- `/api/health` potwierdza, że proces API odpowiada i zwraca `status: ok`.
  Nie dowodzi gotowości wszystkich zależności.
- `/api/system/status` potwierdza, że powierzchnie statusu runtime odpowiadają.
  Skrypt wymaga tylko HTTP 200 i nie czyta ani nie wypisuje pól odpowiedzi.
- `/api/jobs/status` pokazuje informacyjny stan schedulera. Wartości
  `running=false` i `autostart=false` mogą być prawidłowe, ponieważ scheduler
  jest domyślnie wyłączony. Minimalny skrypt go nie odpytuje, więc ten endpoint
  nie wpływa na jego wynik.

Po alarmie uruchom skrypt ręcznie na hoście, sprawdź stan i dziennik jednostki
API, a następnie eskaluj do wskazanego właściciela. Nie restartuj usługi w
pętli bez rozpoznania przyczyny.

To jest hak obserwacyjny, a nie bramka kompletności ani dowód SLA. Produkcyjny
monitoring nadal wymaga decyzji właściciela o kanale odbiorczym, liczbie
kolejnych porażek uruchamiających alarm, czasie reakcji i retencji. Sam wpis
cron lub timer nie dowodzi, że sygnał dotarł do człowieka.
