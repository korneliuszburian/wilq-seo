# WILQ Production Readiness Audit — stan na 2026-08-15

Current-state dokument: mierzy infrastrukturę produkcyjną względem tego, co
CONTEXT.md wprost wymienia jako nieudowodnione (auth, TLS, tenant/actor
contract, monitoring, HA, rotation, maintenance). Opisuje tylko to, co da się
wskazać w kodzie, skryptach i runbookach w tym commicie; nie jest zgodą na
deploy i nie zmienia niczego w produkcji. Decyzje i historię trzyma git i Beads.

## Werdykt

WILQ pozostaje **lokalnym single-tenant pilotem z loopback-only API**. Ma już
operacyjne artefakty monitoringu, restartu, backupu/restore, rotacji,
maintenance i deployu oraz seamy obsługi zbudowanego SPA i schedulera. Są one
sprawdzone w checkoutcie, lecz nadal nie są produkcyjnie zweryfikowane na
docelowym hoście. Otwarte pozostają decyzje `OWNER` o L1, L2, L3 i celu L9;
propozycję porządkuje
`docs/architecture/production-target-decision.md`.

## 1. Co istnieje (dowody)

| Wymiar | Stan | Dowód |
| --- | --- | --- |
| Sieciowa brama API | Loopback-only, socket-peer based, `403` dla zdalnego peera | `apps/api/wilq_api/main.py:122-148` (`require_local_api_access` + `_is_loopback_peer`), falsifier `tests/api_contracts/test_loopback_access.py` (remote 403 / local 200 / spoofed Host ignorowany) |
| CORS | Tylko localhost dev originy + regex loopback, `allow_credentials=False` | `apps/api/wilq_api/main.py:60-96` |
| Actor contract | Stały `LOCAL_PILOT_AUDIT_IDENTITY`: `principal=local_operator`, `workspace=ekologus_local_pilot`, `trust=local_unverified` | `wilq/audit/identity.py:7-20` |
| Audit | Niezmienny ślad z actor/principal/workspace/trust polami | `wilq/actions/audit_store.py:174-205` |
| Credential source | `.env` (repo-local) + access-pack fallback; status raportuje nazwy, nie wartości; redaction przed logami/context-pack | `wilq/credentials/runtime.py`, `wilq/security/redaction.py`, `docs/security/credential-handling.md` |
| Runtime status | `credential_runtime_status(detailed=False)`; codex readiness `ready/missing_cli/missing_login` | `apps/api/wilq_api/routers/system.py:38-52`, `wilq/codex/runtime_status.py` |
| Joby | **ZAMKNIĘTE ARTEFAKTEM — S2:** deterministyczne definicje + manualne run endpoints; scheduler startuje w lifespanie API wyłącznie za `WILQ_ENABLE_SCHEDULER` (domyślnie off), a status pokazuje rzeczywiste `running` | `wilq/jobs/scheduler.py`, `apps/api/wilq_api/main.py`, falsifier `tests/test_jobs_scheduler.py` |
| Storage | SQLite `.local-lab/state/wilq.sqlite3` + DuckDB `.local-lab/state/wilq.duckdb`; private paths chmod 600/700; version gate | `wilq/storage/local_state.py:19-28`, `wilq/storage/metric_store.py:28-35`, `wilq/storage/private_paths.py` |
| Backup/restore | Kanoniczny `scripts/backup.sh` kopiuje parę SQLite/DuckDB i porównuje `storage_proof`; restore round-trip do świeżych ścieżek zachowuje proof | `scripts/backup.sh`, `wilq/storage/recovery.py`, falsifier `tests/storage/test_backup_script.py` |
| Codex runtime | Local `codex app-server` na istniejącym `codex login` (`auth.json`), bez API key | `wilq/codex/app_server.py:624-654`, `docs/architecture/codex-runtime.md` |
| Stack i dashboard | **ZAMKNIĘTE ARTEFAKTEM — S1:** `scripts/local_stack.sh start|status|restart|logs|stop`; API może opcjonalnie podać zbudowane SPA za `WILQ_SERVE_DASHBOARD` + `WILQ_DASHBOARD_DIST`, bez zmiany zachowania domyślnego | `scripts/local_stack.sh`, `apps/api/wilq_api/main.py`, falsifier `tests/api_contracts/test_spa_dashboard_serving.py` |
| Supervisor / deploy | Szablony systemd dla API i wariantu ze SPA mają `Restart=always`; runbook definiuje próbę restartu po awarii | `deploy/wilq-api.service`, `deploy/wilq-dashboard.service`, `deploy/README.md`, falsifier `tests/test_deploy_units.py` |
| Monitoring | Hook sprawdza `/api/health` i `/api/system/status`; runbook opisuje cron/timer, reakcję i dowód alertu | `scripts/health_check.sh`, `deploy/monitoring.md`, falsifier `tests/test_health_check_script.py` |
| Runbooki operacyjne | Rotacja poświadczeń oraz maintenance/migracja/recovery mają operatora, zgodę, weryfikację i rollback | `docs/security/rotation-runbook.md`, `docs/infra/maintenance.md`, falsifier `tests/test_ops_runbooks.py` |
| CI | lint, skill hygiene, marketer-language guard, typecheck, full backend tests, security (bandit/pip-audit/semgrep/detect-secrets), `verify.sh` | `.github/workflows/quality.yml` |

## 2. Mapa luk (co jest nieudowodnione albo nie istnieje)

Status **ZAMKNIĘTE ARTEFAKTEM** oznacza, że istnieje kanoniczny artefakt
operacyjny i jego focused proof w checkoutcie. Nie oznacza produkcyjnej
weryfikacji. **OTWARTE — OWNER** oznacza brak decyzji właściciela. Niezależnie
od statusu realna akcja — deploy, crash, alert, rotacja albo restore — na
wybranym hoście nadal zamyka pętlę operacyjną.

| # | Wymiar | Status | Pozostała luka | Dowód do finalnej weryfikacji |
| --- | --- | --- | --- | --- |
| L1 | Auth | **OTWARTE — OWNER** | Jedyną bramą jest loopback socket peer, nie tożsamość aplikacyjna; każdy lokalny proces ma pełny dostęp. | Wybór P2 z proponowanego ADR-a i falsifier zgodny z wyborem. |
| L2 | TLS | **OTWARTE — OWNER** | API i dashboard używają czystego HTTP na loopbacku; brak zaakceptowanej decyzji, czy zdalny dostęp w ogóle powstaje. | Wybór P3: jawne no-TLS dla loopback-only albo sprawdzona terminacja Caddy. |
| L3 | Multi-tenant / actor | **OTWARTE — OWNER** | Jeden stały workspace i nieweryfikowany actor odpowiadają pilotowi, ale status single-user nie został zatwierdzony jako kontrakt. | Wybór P4: single-user albo zweryfikowany actor/workspace dla każdego zapisu. |
| L4 | Monitoring | **ZAMKNIĘTE ARTEFAKTEM — S5** | Istnieją health hook i runbook; kanał odbiorczy, próg, reakcja i retencja zależą od celu. | Wywołany alert dociera do wskazanego człowieka na docelowym hoście. |
| L5 | HA / restart | **ZAMKNIĘTE ARTEFAKTEM — S4** | Systemd zapewnia restart procesu, nie replikację file-based storage; próba z runbooka nie została wykonana na celu. | Crash test daje nowy PID, zdrowe API i zgodne dane na docelowym hoście. |
| L6 | Rotation | **ZAMKNIĘTE ARTEFAKTEM — S6** | Runbook istnieje; nie wykonano autoryzowanej rotacji ani unieważnienia poprzedniego poświadczenia. | Jedna zatwierdzona rotacja z fresh vendor read i bezpiecznym dowodem unieważnienia. |
| L7 | Backup operational | **ZAMKNIĘTE ARTEFAKTEM — S3** | Kanoniczny backup i restore round-trip zachowują `storage_proof`; harmonogram, retencja i lokalizacja zależą od celu. | Zaplanowany backup i restore drill na hoście; dla C kopia off-box. |
| L8 | Maintenance | **ZAMKNIĘTE ARTEFAKTEM — S6** (recovery proof: S3) | Runbook obejmuje migrację, recovery, joby i rollback, lecz nie był wykonany na aktywnym celu. | Autoryzowane okno z backupem, proofem, readbackiem i rollback drill. |
| L9 | Deploy target | **CZĘŚCIOWO ZAMKNIĘTE — S4; CEL OTWARTY — OWNER** | Szablony systemd są gotowe (S4), a API podaje zbudowane SPA (S1); nie wybrano laptopa, serwera LAN ani VPS. | Decyzja P1 w `production-target-decision.md`, instalacja szablonu i deploy proof na wybranym hoście. |

## 3. Co ten dokument NIE dowodzi

- Nie dowodzi, że WILQ jest bezpieczny w sieci publicznej, odporny na awarie
  ani że spełnia jakikolwiek SLA/RODO/bezpieczeństwo produkcyjne.
- Nie jest zgodą na deploy, publikację, vendor write ani secret rotation.
- Status artefaktu nie jest statusem `PASS` produkcji i nie potwierdza SLA.
- L1, L2, L3 oraz wybór celu L9 pozostają otwartymi decyzjami `OWNER`.
- Realne działanie infrastruktury może potwierdzić tylko deploy i właściwa
  próba (crash, alert, rotacja, backup/restore) w docelowym środowisku, nie
  testy w checkoutcie.

## 4. Najbliższy krok

`OWNER` powinien rozpatrzyć propozycję w
`docs/architecture/production-target-decision.md` i jawnie wybrać P1–P4:
środowisko, auth, TLS oraz single-user/actor. Rekomendacja brzmi A — lokalny
pilot; nie jest to jeszcze decyzja. Do wyboru nie należy pisać kolejnego kodu
wdrożeniowego ani wykonywać deployu. Po wyborze najbliższym dowodem jest jedna
realna próba właściwa dla celu: deploy + crash/alert/restore na tym hoście.
