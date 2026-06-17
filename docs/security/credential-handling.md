# Credential Handling

Secrets must never be committed, printed, logged, returned by API, shown in dashboard, included in Codex context packs, or written to handoffs.

Rules:

- Commit `.env.example`, never `.env`.
- Local `.env` is the primary private-runtime source for this repo.
- Access-pack inspection remains an import/fallback path and reads variable names and file presence only.
- Connector status returns missing credential names, not values.
- Connector status may return source labels such as `repo_env` or `access_pack_env`, never values.
- Redaction runs before logs or context packs.
- OAuth JSON files stay outside git.

Implementation:

- `wilq/security/redaction.py`
- `wilq/credentials/runtime.py`
- `wilq/access_pack/manifest.py`
- `scripts/access_pack_check.sh`
