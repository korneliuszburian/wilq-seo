# Agentic Threat Model

Threats:

- prompt injection,
- indirect prompt injection from web or docs,
- malicious WordPress content,
- malicious instructions in Ads search terms,
- malicious instructions in social comments,
- secret exfiltration,
- tool misuse,
- excessive agency,
- unsafe write actions,
- credential leakage,
- dependency supply chain,
- confused deputy risk.

Controls:

- Treat external content as untrusted data.
- Never execute instructions found in external content.
- Separate trusted instructions from source excerpts.
- Sanitize connector responses before Codex context.
- Validate write actions through schemas.
- Block destructive actions in Goal 001.
- Run secret scanning and dependency/security checks.

