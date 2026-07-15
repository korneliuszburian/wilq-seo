# WILQ Marketing Operating System

Local API-first marketing command center for Ekologus.

WILQ API is the system brain. The dashboard, Codex skills, hooks, connector registry, expert rules, opportunities, and action objects must all use the same typed contracts.

## Quick Start

```bash
uv sync --all-extras
pnpm install
scripts/verify.sh
```

Run the canonical local API and dashboard stack:

```bash
scripts/local_stack.sh start
```

Inspect its managed processes and readiness:

```bash
scripts/local_stack.sh status
```

The known Ekologus access pack is expected at:

```txt
/home/krn/ekologus-access-pack-20260617-120758
```

Do not copy secrets from the access pack into committed files.
