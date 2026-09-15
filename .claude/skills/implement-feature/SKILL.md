---
name: implement-feature
description: Bounded Level-1 build loop for one human-approved Info-Harbor spec — implement the smallest change, validate offline, correct up to five times per invocation, then stop at reviewing and hand off to /review-feature implementation. Never invokes the reviewer, never writes an implementation review, never sets human_review, and never merges, pushes, or deploys.
argument-hint: <feature-slug>
disable-model-invocation: true
---

# /implement-feature

Arguments: `$ARGUMENTS` — the feature slug. The spec is
`features/<slug>/spec.md`.

You are the **builder**. You may not mark your own work `done`, and you may
not declare it verified — only the independent `feature-reviewer` can return
`PASS`, and only `/review-feature implementation <slug>` may invoke it, record
its verdict, and advance the queue past `reviewing`.

## Absolute limits

- Never merge, push, open or merge a PR, deploy, force-push, or delete a
  branch.
- Never touch `main` or `.github/workflows/deploy.yml`.
- Never run an entry point listed in `AGENTS.md` §2, open `keys/`, create or
  modify credentials, or contact BigQuery, Drive, or Secret Manager.
- Never run a destructive or schema migration; never write production data.
- Never discard, revert, stash, or overwrite pre-existing changes you did not
  make.
- Never weaken, skip, delete, or rewrite a test to make a failure disappear.
- Commit only if the user has explicitly authorized committing in this
  session (`AGENTS.md` §3). Otherwise leave changes uncommitted and say so.

## Phase 0 — Preconditions (refuse if any fail)

1. Read `AGENTS.md`, `docs/PROJECT_STATE.md`, `features/QUEUE.md`, and the
   whole spec.
2. At least one `verification/spec-review-<n>.md` exists and its latest
   recorded verdict is `PASS`. If none exists, or the latest recorded verdict
   is not `PASS`: stop, do not build. Set the queue to `blocked` with a note
   that spec review is required, and hand off to `/review-feature spec
   <slug>`.
3. The spec's **Approval** section says `Approved: yes`, with a name and date.
   If not: stop, report "spec not approved", change nothing.
4. No **blocking** open question is unanswered. If one is: stop, set the
   queue to `blocked` with the question in the note.
5. The queue status is `ready`, `building`, or `reviewing`. If it is anything
   else, stop and report why.
6. Count the `verification/implementation-review-*.md` records that recorded a
   `FAIL`. If **3** or more exist, the three-round review bound is exhausted:
   stop, set the queue to `blocked`, summarize the rounds, and hand off to the
   human.

## Phase 1 — Protect the working tree

1. Run `git status`, `git branch --show-current`, `git diff --stat`,
   `git diff --cached --stat`, and list untracked files. Record them in
   `verification/pre-existing-state-<n>.md`, with `<n>` derived by the single
   numbering rule in `verification/README.md` (highest existing
   `pre-existing-state-*.md` + 1, or `1` when none exists). Never write this
   inventory into a validation file.
2. Pre-existing modifications that the spec does not cover are **not yours**:
   do not edit, stage, or revert them, and exclude them from every claim you
   make about your diff.
3. Branch: the spec names a proposed branch and base. If you are not already
   on it:
   - if the working tree has no uncommitted changes, **recommend** the exact
     command (`git switch -c <branch> <base>`) and create it only if the user
     has authorized branching in this session;
   - if uncommitted changes exist, do **not** switch; stop and ask.
4. Set the queue row to `building` with the branch name.

## Phase 2 — Inspect before editing

Read every file in the spec's "Files likely to change", their live callers,
and existing tests. Confirm each live entry point. If reality contradicts the
spec in a way that changes scope or behavior, stop, set `blocked`, and report
the contradiction — do not silently redesign.

## Phase 3 — Build (smallest change)

- Make the smallest change that satisfies the acceptance criteria.
- Preserve behavior outside the approved scope and output parity
  (`docs/modernization-spec.md` §6) unless the spec approves a cited exception.
- Follow the repository's conventions in `AGENTS.md` (explicit-path
  `importlib` loading instead of new `sys.path` mutation, injected clocks and
  seeds in tests, no new catch-all `utils`).
- Add or update offline tests that call the real production function and
  would fail without the change.
- Update `docs/code-audit.md` and `docs/modernization-log.md` as `AGENTS.md` §7
  requires, in the same change.

## Phase 4 — Validate and correct (bounded loop)

Derive the starting `n` by the same numbering rule
(`verification/README.md`): one more than the highest existing
`validation-*.md` for this feature, or `1` when none exists. A re-invocation
therefore continues the sequence instead of overwriting an earlier cycle's
record.

Repeat, starting at that `n`:

1. Run every command in the spec's "Automated verification" section and
   verification map. Always include:
   - `python -m pytest -q` (or `.venv/Scripts/python.exe -m pytest -q` on this
     Windows checkout when the system interpreter lacks pinned dependencies —
     record which);
   - `python -m compileall -q projects shared ui tests campaign_manager.py`;
   - `git check-ignore -q tests/conftest.py` (must exit 1);
   - `git ls-files | grep '^keys/'` (must print nothing).
2. Write `verification/validation-<n>.md` using the command-record format in
   `verification/README.md`.
3. If everything passes: go to Phase 5.
4. If something fails: find the **root cause** (read the traceback and the
   code; reproduce narrowly). Record the diagnosis and the correction in the
   same validation file. Do not mask it with try/except, skips, `xfail`,
   loosened assertions, or pinned-around symptoms. Determine whether the
   failure pre-existed your change (check against the base commit's recorded
   baseline) and say so.
5. `n += 1`. If **5** unsuccessful correction cycles have happened **in this
   invocation** (or the spec's lower retry limit), stop: set the queue to
   `blocked`, summarize every attempt and the current hypothesis, and hand off
   to the human. The bound counts cycles in this invocation; the record
   numbers keep increasing across invocations.

## Phase 5 — Hand off for independent review

1. Set the queue row to `reviewing`, and record in its Verification column
   which `verification/validation-<n>.md` is the passing record.
2. Stop there. You **never** invoke `feature-reviewer`, **never** write
   `verification/implementation-review-<n>.md`, and **never** set
   `human_review`: the independent implementation review is performed and
   recorded only by `/review-feature implementation <slug>`, which is also the
   only thing that may move the row to `human_review`
   (`features/README.md` Rules; `AGENTS.md` §18).
3. Hand off the exact next action: `/review-feature implementation <slug>`.
   If that review returns `FAIL` it sets the row back to `building`, and
   `/implement-feature <slug>` is run again — its Phase 0 check stops the work
   as `blocked` once three `FAIL` rounds have been recorded.

## Final report

- Branch, base, and `git status`
- Files changed (yours) vs. pre-existing changes (not yours)
- Each acceptance criterion and its evidence file
- Validation cycles used in this invocation, and the record numbers written
  (`pre-existing-state-<n>.md`, `validation-<n>.md`)
- The path to the passing validation record; no reviewer verdict, because this
  skill does not run the reviewer
- Confirmation that nothing was merged, pushed, or deployed
- `Status / Blockers / Handoff` footer (`AGENTS.md` §8), handing off
  `/review-feature implementation <slug>`
