# Verification Evidence — conventions

Everything a reviewer or a human needs to confirm this feature's acceptance
criteria without trusting anyone's summary lives here.

## Files

| File | Written by | Contents |
|---|---|---|
| `spec-review-<n>.md` | `/review-feature spec` | Verdict (`PASS`/`FAIL`), blocking findings, non-blocking improvements |
| `pre-existing-state-<n>.md` | `/implement-feature` (Phase 1) | The working tree as found before any edit: branch, `git status`, staged and unstaged diffs, untracked files |
| `validation-<n>.md` | `/implement-feature` | One per validation cycle: every command, exit code, pass/fail counts, failure summary, root cause and correction |
| `implementation-review-<n>.md` | `/review-feature implementation` | Reviewer verdict, per-acceptance-criterion results, findings |
| `manual-<topic>.md` | Builder or human | Manual verification steps actually performed and what was observed |
| `*.png` | Builder | Screenshots, only when a UI acceptance criterion needs one |

**Numbering rule — one rule for every numbered family above.** `<n>` is
*derived, never assumed*: before writing a numbered record, list the existing
files of that family and use the highest existing number + 1, or `1` when none
exists. Never overwrite an earlier record, including across re-invocations of
the same skill.

## Required shape of a command record

```markdown
### <short purpose>
- Command: `python -m pytest -q`
- Working directory: repository root
- Git state: <branch> @ <short sha>, <clean | list of modified files>
- Exit code: 0
- Result: 278 passed, 17 warnings
- Relevant output: <trimmed excerpt, or "none">
- Pre-existing failure? <yes/no/not applicable — cite evidence>
```

Record the command that was actually run, exactly. Do not paraphrase a result
you did not observe.

## Must never appear in evidence

- Secret values, tokens, service-account content, or anything from `keys/`.
- Raw device identifiers (DIDs) or real campaign data pulled from production.
- Output from running a prohibited entry point (`AGENTS.md` §2) — those must
  not be run at all.

## Gitignore caveats

The root `.gitignore` excludes `*.json`, `*.log`, `*.env`, and `*.config`
repository-wide. Evidence saved with those extensions will silently not be
committed. Save evidence as `.md` or `.txt`.
