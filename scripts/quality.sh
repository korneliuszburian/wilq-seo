#!/usr/bin/env bash
set -euo pipefail

scripts/lint.sh
uv run python scripts/verify_content_status_214.py
uv run python scripts/skill_hygiene_check.py
uv run python scripts/marketer_language_guard.py
scripts/typecheck.sh
