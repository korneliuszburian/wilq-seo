# Quality Gates

Quality gates must catch realistic product failures:

- invalid schemas,
- missing source connectors,
- missing evidence IDs,
- unsafe write actions,
- secret leaks,
- bad imports,
- type errors,
- broken dashboard routes,
- broken API contracts,
- Codex output not matching schema.

Commands:

```bash
scripts/lint.sh
scripts/typecheck.sh
scripts/test.sh
scripts/security.sh
scripts/quality.sh
scripts/verify.sh
```

Goal 001 allows skipped external security tools only when the command is unavailable, and the script must report that honestly.

