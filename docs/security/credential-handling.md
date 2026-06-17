# Credential Handling

Secrets must never be committed, printed, logged, returned by API, shown in dashboard, included in Codex context packs, or written to handoffs.

Rules:

- Commit `.env.example`, never `.env`.
- Access-pack inspection reads variable names and file presence only.
- Connector status returns missing credential names, not values.
- Redaction runs before logs or context packs.
- OAuth JSON files stay outside git.

Implementation:

- `wilq/security/redaction.py`
- `wilq/access_pack/manifest.py`
- `scripts/access_pack_check.sh`

