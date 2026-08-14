# WILQ Production Readiness Audit — stan na 2026-08-14

Current-state dokument: mierzy infrastrukturę produkcyjną względem tego, co
CONTEXT.md wprost wymienia jako nieudowodnione (auth, TLS, tenant/actor
contract, monitoring, HA, rotation, maintenance). Opisuje tylko to, co da się
wskazać w kodzie i skryptach w tym commicie; nie jest zgoda na deploy i nie
zmienia niczego w produkcji. Decyzje i historię trzyma git i Beads.

## Werdykt

WILQ jest **lokalnym single-tenant pilotem z loopback-only API i jawną
luką dowodową na produkcję**. Istniejące kontrole są realne i przetestowane
(loopback gate, redaction, backup-with-proof, deterministyczne joby), ale
żaden z wymiarów produkcyjnych nie jest udowodniony przez deploy, obciążenie
czy awarię poza lokalnym checkoutem.

## 1. Co istnieje (dowody)

| Wymiar | Stan | Dowód |
| --- | --- | --- |
| Sieciowa brama API | Loopback-only, socket-peer based, `403` dla zdalnego peera | `apps/api/wilq_api/main.py:122-148` (`require_local_api_access` + `_is_loopback_peer`), falsifier `tests/api_contracts/test_loopback_access.py` (remote 403 / local 200 / spoofed Host ignorowany) |
| CORS | Tylko localhost dev originy + regex loopback, `allow_credentials=False` | `apps/api/wilq_api/main.py:60-96` |
| Actor contract | Stały `LOCAL_PILOT_AUDIT_IDENTITY`: `principal=local_operator`, `workspace=ekologus_local_pilot`, `trust=local_unverified` | `wilq/audit/identity.py:7-20` |
| Audit | Niezmienny ślad z actor/principal/workspace/trust polami | `wilq/actions/audit_store.py:174-205` |
| Credential source | `.env` (repo-local) + access-pack fallback; status raportuje nazwy, nie wartości; redaction przed logami/context-pack | `wilq/credentials/runtime.py`, `wilq/security/redaction.py`, `docs/security/credential-handling.md` |
| Runtime status | `credential_runtime_status(detailed=False)`; codex readiness `ready/missing_cli/missing_login` | `apps/api/wilq_api/routers/system.py:38-52`, `wilq/codex/runtime_status.py` |
| Joby | Deterministyczne definicje + manualne run endpoints; APScheduler `autostart=False` | `wilq/jobs/scheduler.py:15-42`, `apps/api/wilq_api/routers/jobs.py` |
| Storage | SQLite `.local-lab/state/wilq.sqlite3` + DuckDB `.local-lab/state/wilq.duckdb`; private paths chmod 600/700; version gate | `wilq/storage/local_state.py:19-28`, `wilq/storage/metric_store.py:28-35`, `wilq/storage/private_paths.py` |
| Backup/migration seam | `copy_sqlite_store`/`copy_duckdb_store` + `storage_proof` porównujący przed/po; wymaga `approved_maintenance_window` | `wilq/storage/recovery.py`, `wilq/storage/semantic_review_activation.py:44-98` |
| Codex runtime | Local `codex app-server` na istniejącym `codex login` (`auth.json`), bez API key | `wilq/codex/app_server.py:624-654`, `docs/architecture/codex-runtime.md` |
| Stack | `scripts/local_stack.sh start|status|restart|logs|stop`, loopback bind wymuszony, runtime files chmod 600/700 | `scripts/local_stack.sh:13-27,41-48,332-410` |
| CI | lint, skill hygiene, marketer-language guard, typecheck, full backend tests, security (bandit/pip-audit/semgrep/detect-secrets), `verify.sh` | `.github/workflows/quality.yml` |

## 2. Mapa luk (co jest nieudowodnione albo nie istnieje)

Każdy wiersz: wymiar, czego brakuje, dlaczego to luka, i jaki dowód zamknąłby
ją. Brak wiersza nie znaczy "gotowe"; oznacza "nie mierzone w tym commicie".

| # | Wymiar | Luka | Dowód do zamknięcia |
| --- | --- | --- | --- |
| L1 | Auth | Brak autoryzacji na poziomie aplikacji: jedyną bramą jest loopback socket peer. Brak API key, OAuth, sesji, per-actor auth. Każdy proces lokalny ma pełny dostęp. | Decyzja o modelu auth (local-only na stale vs key/OAuth przy zdalnym dostępie) + falsifier per decyzja; obecnie loopback gate jest tylko sieciowy, nie tożsamościowy. |
| L2 | TLS | API i dashboard wystawione jako czyste HTTP na loopbacku (`http://127.0.0.1:8000`/`5173`); brak certów i terminacji TLS. | Świadoma decyzja "loopback-only nie wymaga TLS" albo TLS termination przy zdalnym dostępie; dowód w deploy konfiguracji. |
| L3 | Multi-tenant / actor | Jeden stały workspace `ekologus_local_pilot` i trust `local_unverified`; `submitted_actor_label` pochodzi z requesta bez weryfikacji. To single-tenant Ekologus z zamierzenia, ale nie ma kontraktu rozróżniającego actora. | Osobny kontrakt actor/workspace dla każdego zapisu audytowego (potwierdzenie, że `reviewed_by`/`confirmed_by` to prawdziwy podmiot) albo jawna decyzja, że pilot zostaje single-user. |
| L4 | Monitoring | Brak strukturalnych logów, metryk (np. Prometheus), alertów, retention i SLA; istnieją tylko health/status endpoints (`/api/health`, `/api/system/status`, `/api/jobs/status`). | Kto patrzy na te endpointy, kiedy i z jakim progiem; dowód z alertu/runbooku, nie tylko endpoint. |
| L5 | HA | Pojedynczy proces uvicorn na loopbacku, brak restart supervisor (systemd/PM2/kubernetes), brak replikacji storage (SQLite/DuckDB file-based). | Dowód restartu po awarii i odzyskania danych (crash injection) w docelowym środowisku; obecnie działa tylko `local_stack.sh stop/start` ręcznie. |
| L6 | Rotation | Brak procedure secret rotation (hasła app-password WordPress, tokeny OAuth, access-pack). | Runbook rotacji z dowodem wykonania i unieważnieniem starych poświadczeń. |
| L7 | Backup operational | Istnieje backup-with-proof na seam aktywacji semantic review, ale brak regularnego harmonogramu backupów SQLite/DuckDB dla pilota. | Harmonogram backupu + test restauracji (przywrócenie z kopii na świeżym katalogu). |
| L8 | Maintenance | Jedyny maintenance seam to `approved_maintenance_window` w `semantic_review_activation.py`; brak reszty runbooków (migracje schematu, odzyskiwanie po partial write). | Runbook migracji i recovery z dowodem wykonania; normalny runtime nie powinien dotykać backup/migracji. |
| L9 | Deploy target | Brak jakiegokolwiek artefaktu deployu (Dockerfile/systemd/k8s/ansible); `local_stack.sh` zakłada lokalny checkout dewelopera z `uv` i `pnpm`. | Świadoma definicja środowiska docelowego (laptop Wilka vs serwer) i artefakt, który się tam instaluje. |

## 3. Co ten dokument NIE dowodzi

- Nie dowodzi, że WILQ jest bezpieczny w sieci publicznej, odporny na awarie
  ani że spełnia jakikolwiek SLA/RODO/bezpieczeństwo produkcyjne.
- Nie jest zgodą na deploy, publikację, vendor write ani secret rotation.
- Mapuje luki i istniejące kontrole; każdy wiersz z sekcji 2 ma otwarty
  "Dowód do zamknięcia", więc brak PASS w wymiarze produkcyjnym.
- Realne działanie infrastruktury (auth, TLS, monitoring, HA, backup) może
  potwierdzić tylko uruchomienie w docelowym środowisku + awaria testowa,
  nie testy w checkoutcie.

## 4. Najbliższy krok

Przed jakimkolwiek deployem wybrać środowisko docelowe (L9), rozstrzygnąć
model auth (L1) i TLS (L2) razem, a następnie zbudować restart+backup proof
(L5, L7). To są decyzje własnościowe (człowiek), nie kod do napisania na
ślepo; żadna z nich nie jest jeszcze autoryzowana.
