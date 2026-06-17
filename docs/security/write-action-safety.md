# Write Action Safety

Write actions must go through ActionObject validation and audit logging.

Goal 001 supports preparation and validation foundations only. It does not implement destructive external writes.

Controls:

- Evidence IDs required.
- Connector configured state required.
- Payload validation required.
- Audit event required.
- High/critical risk writes blocked.
- Destructive actions blocked.

