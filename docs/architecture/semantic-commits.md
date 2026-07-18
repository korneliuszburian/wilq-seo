# Semantic commits

WILQ uses Conventional-Commit-style headers for every new commit:

```text
<type>(optional-scope): <lowercase imperative description>
```

Allowed types are `feat`, `fix`, `docs`, `refactor`, `refine`, `perf`, `test`, `build`,
`ci`, `chore`, `revert` and `style`. (`refine` is WILQ's existing focused
polish type.) The subject is at most 100 characters and
does not end with a period.

Existing history contains older non-semantic headers, plus a small number of
legacy project types. It remains immutable and
is not rewritten without explicit publication authority. New commits are
guarded by `.githooks/commit-msg`; enable the tracked hook once in a checkout:

```bash
git config core.hooksPath .githooks
```

The guard checks commit-message shape only. It does not replace code review,
focused proof, Beads ownership or publication approval.
