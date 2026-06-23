#!/usr/bin/env bash
set -euo pipefail

scripts/lint.sh
uv run python scripts/skill_hygiene_check.py
scripts/typecheck.sh
scripts/test.sh
