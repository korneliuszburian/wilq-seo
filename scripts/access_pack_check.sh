#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from wilq.access_pack.manifest import access_pack_status

status = access_pack_status()
print(f"exists={status['exists']}")
print(f"env_file_present={status['env_file_present']}")
print(f"env_key_count={status['env_key_count']}")
print(f"credential_file_count={status['credential_file_count']}")
print(f"manifest_file_count={status['manifest_file_count']}")
print("secrets_redacted=true")
PY
