# Model Runtime Policy

Do not hardcode product correctness to one model. Codex is the primary operator runtime, but WILQ API must stay model-independent.

Policy:

- Skills call API contracts, not hidden model behavior.
- Critical workflows define output schemas.
- `codex exec` smoke tests validate schema, not prose quality only.
- Runtime unavailability must expose status and fallback path.
- Model changes cannot bypass evidence/action validation.

Implementation:

- `wilq/codex/model_policy.py`
- `wilq/codex/runtime_status.py`

