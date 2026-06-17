#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import os

from wilq.access_pack.manifest import access_pack_status, env_key_names

status = access_pack_status(detailed=os.getenv("WILQ_ACCESS_PACK_DIAGNOSTIC") == "1")
print("env_keys:")
for key in sorted(env_key_names()):
    print(f"- {key}")
if "manifest_files" in status:
    print("files:")
    for name in status["manifest_files"]:
        print(f"- {name}")
else:
    print(f"manifest_file_count={status['manifest_file_count']}")
print("values: redacted")
PY
