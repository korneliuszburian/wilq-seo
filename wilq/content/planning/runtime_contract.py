from __future__ import annotations

from os import environ

DEFAULT_PLANNING_CODEX_TIMEOUT_SECONDS = 300.0
# Keep the deadline in one contract. The async API returns a queued state, so
# five minutes gives a complete evidence-bound plan enough room for a larger
# inventory without making the browser request itself wait. The explicit zero
# grace keeps stale-job recovery tied to the same bounded Codex deadline.
PLANNING_JOB_STALE_GRACE_SECONDS = 0.0


def planning_codex_timeout_seconds() -> float:
    try:
        configured = float(
            environ.get(
                "WILQ_PLANNING_CODEX_TIMEOUT_SECONDS",
                str(DEFAULT_PLANNING_CODEX_TIMEOUT_SECONDS),
            )
        )
    except ValueError:
        configured = DEFAULT_PLANNING_CODEX_TIMEOUT_SECONDS
    return max(5.0, configured)


def planning_job_stale_after_seconds() -> float:
    return planning_codex_timeout_seconds() + PLANNING_JOB_STALE_GRACE_SECONDS


__all__ = [
    "DEFAULT_PLANNING_CODEX_TIMEOUT_SECONDS",
    "PLANNING_JOB_STALE_GRACE_SECONDS",
    "planning_codex_timeout_seconds",
    "planning_job_stale_after_seconds",
]
