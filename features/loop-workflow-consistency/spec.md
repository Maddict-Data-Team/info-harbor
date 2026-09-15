# Feature: Loop workflow consistency fixes

> **Retroactive spec.** The work this spec describes was already implemented
> directly, as a human-directed correction, before this spec was written — it
> did not go through `/plan-feature` → `/implement-feature`. This document
> exists to route already-built work through the normal review process, the
> same way `docs/PROJECT_STATE.md`'s "Phase A safety contracts" row already
> does for other pre-loop work: `features/QUEUE.md`'s Phase A row records
> "Next: retroactive spec, then `/review-feature implementation`" as the
> precedent. For this feature the path is: retroactive spec (this file) →
> `/review-feature spec` → (skip `/implement-feature` — there is nothing left
> to build) → `/review-feature implementation` against the existing diff and
> validation evidence already on disk. This is not a new one-off exception; it
> reuses the pattern the repository already applies to Phase A.

| Field | Value |
|---|---|
| Slug | `loop-workflow-consistency` |
| Queue status | `reviewing` |
| Related audit findings | none — capability/process work |
| Proposed branch | none — this is a direct correction living on the existing setup branch, not a new branch |
| Base branch | `chore/loop-engineering-setup` @ `0bf25f4` |
| Spec author | Authored retroactively by the agent directing this correction, on behalf of and at the direction of the human who ordered the fixes |
| Last updated | 2026-09-15 |

## Approval

> Filled in **only by a human**. `/implement-feature` refuses to start while
> any field here is blank or `Approved` is not `yes`.

This section is genuinely required and currently **pending** — it is not
waived, skipped, or treated as not applicable. The build already happened
directly (see the note above), so `/implement-feature` is not the skill that
will act on this approval, but the human sign-off itself is still required
before this feature is considered accepted: a human must review this spec
and the diff/evidence it describes, then fill in this section themselves.
Awaiting that now.

- Approved: `<yes | no>`
- Approved by: `<name>`
- Date: `YYYY-MM-DD`
- Approval scope / conditions: `<e.g. "parity exception for IH-### approved">`

## Background

The loop-engineering workflow (`features/`, `.claude/skills/plan-feature`,
`.claude/skills/implement-feature`, `.claude/skills/review-feature`,
`.claude/agents/feature-reviewer.md`) was added to this repository as
uncommitted work on `chore/loop-engineering-setup` @ `0bf25f4`
(`docs/PROJECT_STATE.md:4`). Once written, the workflow documents themselves
were found to contain five internal-consistency defects, fixed across two
human-directed correction rounds (this spec covers both):

1. **Evidence-file overwrite (round 1).** Before the fix,
   `.claude/skills/implement-feature/SKILL.md:48,82,92,113` told Phase 1 to
   record the pre-existing working-tree inventory into
   `verification/validation-1.md`, then had Phase 4 start numbering at `n=1`
   and write `verification/validation-<n>.md` — overwriting the same file —
   while Phase 5 referenced an undefined `implementation-review-<r>.md`
   counter. This contradicted "never overwrite an earlier cycle's record" in
   `features/_template/verification/README.md`. Now fixed: the pre-existing
   inventory has its own family, `verification/pre-existing-state-<n>.md`
   (`.claude/skills/implement-feature/SKILL.md:53-58`), and one single
   numbering rule governs every numbered evidence family
   (`features/_template/verification/README.md:17-21`), which Phase 4 derives
   from explicitly (`.claude/skills/implement-feature/SKILL.md:93-97`).
2. **`human_review` ownership contradiction (round 1).** Before the fix,
   `features/README.md:59` said only `/review-feature` may set `human_review`
   while `.claude/skills/implement-feature/SKILL.md:120-122` (pre-fix line
   numbers) told the builder to set it directly. Now fixed: one rule applies
   everywhere — the independent implementation review is performed and
   recorded **only** by `/review-feature implementation <slug>`, which is also
   the only step that may set `human_review`
   (`features/README.md:73-76`; `.claude/skills/implement-feature/SKILL.md:124-133`;
   `.claude/skills/review-feature/SKILL.md:25-36`; `AGENTS.md:318-327`).
3. **Stale branch/state references (round 1).** Before the fix,
   `features/QUEUE.md:20` and `docs/PROJECT_STATE.md:4` (pre-fix wording)
   described the loop-engineering setup as not yet on its own branch, when the
   branch move (`chore/loop-engineering-setup` @ `0bf25f4`) had already
   happened. Now fixed: `features/QUEUE.md:20` and `docs/PROJECT_STATE.md:4`
   both correctly record the branch as existing and the work as uncommitted on
   it, and `docs/modernization-log.md`'s "Loop-engineering setup" entry heading
   was corrected to match (`docs/modernization-log.md:216`).
4. **Missing spec-review gate before implementation (round 2, this round).**
   `.claude/skills/implement-feature/SKILL.md` Phase 0 previously only checked
   that an existing spec-review record, if any, was not an unresolved `FAIL`
   — it did not require one to exist at all, so a spec could reach
   `/implement-feature` with no adversarial spec review ever having run. Now
   fixed: Phase 0 item 2 requires at least one
   `verification/spec-review-<n>.md` whose latest recorded verdict is `PASS`,
   or the skill stops and sets the queue to `blocked`
   (`.claude/skills/implement-feature/SKILL.md:36-40`). The same rule is now
   stated in `AGENTS.md:310-311`, `CLAUDE.md:60-62`, and
   `features/README.md:69-70`.
5. **Inaccurate evidence in `validation-1.md` (round 2, this round).**
   `features/loop-workflow-consistency/verification/validation-1.md:7-13`
   (pre-fix wording) described the working tree as carrying "~57 pre-existing
   modified files from earlier work" — an approximation presented without an
   exact count. Now fixed: the paragraph states the exact, itemized count (55
   pre-existing modified tracked files, none touched by this feature) and
   points to `verification/validation-2.md`, which lists every one of them by
   name plus the untracked `.codex/` mirrors and
   `projects/automation/test_backend_upload.py` in their own categorized
   buckets.

## Problem

A workflow meant to make feature changes auditable and reviewable was itself
carrying defects that undermined those guarantees: evidence could be silently
overwritten, two documents disagreed about who is allowed to advance a feature
to `human_review`, status documents contradicted the actual branch state, the
implementation skill could be invoked without any independent spec review ever
having occurred, and a piece of its own evidence record was an unverified
approximation. Left uncorrected, any of these would let a later feature (or
this one) reach `done` on a false record.

## Goal

Make the loop-engineering workflow documents internally consistent and their
own evidence accurate, then route this already-completed correction through
the same adversarial review every other feature uses, per the Phase A
precedent for retroactive work.

## User stories

- As a builder running `/implement-feature`, I want a hard requirement that
  spec review already passed, so that I cannot start building against a spec
  no one has adversarially checked.
- As a human reviewing this branch, I want the workflow's own evidence files
  to state exact facts (not approximations) about the working tree, so that I
  can trust the evidence the workflow itself produces.
- As a future planner or builder, I want one unambiguous statement of who may
  set `human_review` and how evidence is numbered, so that I don't have to
  reconcile two contradicting documents.

## In scope

- Markdown-only edits, on `chore/loop-engineering-setup`, to:
  `.claude/skills/implement-feature/SKILL.md`, `.claude/skills/review-feature/SKILL.md`,
  `features/README.md`, `features/_template/verification/README.md`,
  `AGENTS.md`, `CLAUDE.md`, `features/QUEUE.md`, `docs/PROJECT_STATE.md`,
  `docs/modernization-log.md`.
- The five fixes enumerated in Background.
- The retroactive spec itself, and the queue/README updates that point to it.
- Recording accurate, itemized validation evidence (this round's
  `verification/validation-2.md`).

## Out of scope

- Everything else in the repository, including any `docs/code-audit.md`
  finding (this is finding-less workflow-consistency work per `CLAUDE.md`'s
  "finding-less capability work needs a log entry only" rule).
- Any production cloud access — no BigQuery, Drive, or Secret Manager call
  (`AGENTS.md` §2).
- Committing, staging, pushing, branching, or merging (`AGENTS.md` §3, §9).
- Building or deploying anything (`AGENTS.md` §9, §22).
- The 55 pre-existing, unrelated modified tracked files already in this
  working tree from earlier work — listed but not touched
  (`verification/validation-2.md`).

## Functional requirements

| ID | Requirement |
|---|---|
| FR-1 | `verification/README.md` (or the family-specific instruction) states one single numbering rule used by every numbered evidence family, and no skill instructs writing over an existing numbered file. |
| FR-2 | Exactly one document states who may set `human_review`, and every other document that mentions it agrees with that statement instead of repeating conflicting instructions. |
| FR-3 | `features/QUEUE.md` and `docs/PROJECT_STATE.md` state the actual current branch and commit for the loop-engineering setup, matching `git rev-parse --abbrev-ref HEAD` and `git rev-parse --short HEAD`. |
| FR-4 | `/implement-feature`'s Phase 0 refuses to proceed unless at least one `verification/spec-review-<n>.md` exists with a latest recorded verdict of `PASS`; `AGENTS.md`, `CLAUDE.md`, and `features/README.md` state the same rule. |
| FR-5 | `features/loop-workflow-consistency/verification/validation-1.md` states an exact, sourced count of pre-existing modified tracked files rather than an approximation, with a pointer to the itemized list. |

## UI and interaction requirements

Not applicable — no UI change.

## Loading, empty, validation, error, and success states

| State | Trigger | Observable behavior (message, HTTP status, exit code, log line) |
|---|---|---|
| Validation error (FR-4) | `/implement-feature <slug>` invoked with no `spec-review-<n>.md`, or the latest one is not `PASS` | Skill stops, queue row set to `blocked`, note says spec review is required, hands off to `/review-feature spec <slug>` |
| Success (FR-4) | `/implement-feature <slug>` invoked with a recorded `spec-review-<n>.md` verdict `PASS` | Phase 0 item 2 passes; the skill proceeds to the remaining preconditions |
| Success (FR-1–FR-3, FR-5) | A reader or reviewer reads the corrected documents | Text matches the actual, current repository state (`git status`, `git branch`) with no contradiction between documents |

Not applicable beyond the above — this is a documentation-consistency fix,
not a running program with runtime states.

## Accessibility requirements

Not applicable — no UI change.

## Security and privacy considerations

- Credentials / `keys/` / Secret Manager touched? No.
- New write path to BigQuery or Drive? No.
- New input reaching SQL or a Drive query string (`IH-030`)? No.
- Authentication impact on `ui/app.py` routes (`IH-025`)? No.
- No secrets, tokens, DIDs, or sensitive query values appear in any edited
  file or in `verification/validation-2.md`.

## Data and migration impact

- BigQuery schema change: none.
- Output parity impact (`docs/modernization-spec.md` §6): none — Markdown
  only, no production code, test, configuration, or dependency file touched.
- Drive structure change: none.
- Migration / backfill needed: none.

## Files likely to change

| File | Why | Live entry point that reaches it (verified) |
|---|---|---|
| `.claude/skills/implement-feature/SKILL.md` | FR-1, FR-4 | Invoked by a human or agent running `/implement-feature <slug>` |
| `.claude/skills/review-feature/SKILL.md` | FR-2 | Invoked by `/review-feature <mode> <slug>` |
| `features/README.md` | FR-1, FR-2, FR-4 | Read by every skill and by humans as the workflow's rulebook |
| `features/_template/verification/README.md` | FR-1 | Read by every skill before writing a numbered evidence file |
| `AGENTS.md` | FR-2, FR-4 | Canonical instructions read by every agent, per `CLAUDE.md:3-7` |
| `CLAUDE.md` | FR-2, FR-4 | Compact pointer read by Claude Code at session start |
| `features/QUEUE.md` | FR-3, and pointing the row at this spec | Read by every skill and human as the loop's source of truth for state |
| `docs/PROJECT_STATE.md` | FR-3 | Read by `/plan-feature`, `/implement-feature`, and humans as the audited snapshot |
| `docs/modernization-log.md` | AGENTS.md §7 documentation requirement | Read by humans and `feature-reviewer` for change history |
| `features/loop-workflow-consistency/verification/validation-1.md` | FR-5 | Read by `feature-reviewer` and humans as evidence |
| `features/loop-workflow-consistency/verification/validation-2.md` (new) | FR-5 | Same |
| `features/loop-workflow-consistency/README.md` | Points at the new spec | Read by humans as the feature's index |

## Dependencies

- Depends on the loop-engineering workflow itself already existing
  (uncommitted on `chore/loop-engineering-setup` @ `0bf25f4`).
- Depends on the Phase A precedent for retroactive specs
  (`features/QUEUE.md`'s Phase A safety contracts row).

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A future reader assumes this feature went through normal `/plan-feature` → human-approval → `/implement-feature` and infers an approval that never happened | Low | Medium — could mislead a future audit | This spec states the retroactive nature and blank Approval section explicitly, at the top and in the Approval section itself |
| The exact pre-existing-file count (55) drifts if someone else edits the working tree between this spec and its review | Low | Low — evidence is a snapshot, not a permanent claim | `verification/validation-2.md` states the count was observed at a specific time via a specific command, not asserted as permanent |

## Observable acceptance criteria

| ID | Given / When / Then |
|---|---|
| AC-1 | Given `features/_template/verification/README.md`, when read, then it states one single numbering rule for every numbered evidence family, and `.claude/skills/implement-feature/SKILL.md` Phase 1 and Phase 4 both derive `<n>` by that rule (no phase starts at a fixed `n=1` unconditionally). |
| AC-2 | Given `features/README.md`, `.claude/skills/implement-feature/SKILL.md`, `.claude/skills/review-feature/SKILL.md`, and `AGENTS.md` §18, when read together, then all agree that only `/review-feature implementation` may set `human_review`, and `/implement-feature` stops at `reviewing`. |
| AC-3 | Given `features/QUEUE.md` and `docs/PROJECT_STATE.md`, when compared against `git rev-parse --abbrev-ref HEAD` and `git rev-parse --short HEAD` run now, then the branch and commit they cite match. |
| AC-4 | Given `.claude/skills/implement-feature/SKILL.md` Phase 0, when a slug has no `verification/spec-review-<n>.md` or the latest one is not `PASS`, then the documented behavior is: stop, set queue to `blocked`, hand off to `/review-feature spec <slug>` — and `AGENTS.md`, `CLAUDE.md`, `features/README.md` state the same rule. |
| AC-5 | Given `features/loop-workflow-consistency/verification/validation-1.md`, when read, then its Git-state paragraph states an exact count (not "~N") of pre-existing modified tracked files, sourced to `verification/validation-2.md`, and `validation-2.md` itemizes every one of them plus the `.codex/` and `test_backend_upload.py` buckets. |

## Verification map

| AC | Method (automated test / command / manual step) | Evidence file |
|---|---|---|
| AC-1 | Manual read of `features/_template/verification/README.md:17-21` and `.claude/skills/implement-feature/SKILL.md:53-58,93-97` | `verification/validation-2.md` |
| AC-2 | Manual read of the four cited files/sections; `grep -rn "human_review"` across them shows one consistent rule | `verification/validation-2.md` |
| AC-3 | `git rev-parse --abbrev-ref HEAD` and `git rev-parse --short HEAD`, compared against `features/QUEUE.md:20` and `docs/PROJECT_STATE.md:4` | `verification/validation-2.md` |
| AC-4 | Manual read of `.claude/skills/implement-feature/SKILL.md:36-40`, `AGENTS.md:310-311`, `CLAUDE.md:60-62`, `features/README.md:69-70` | `verification/validation-2.md` |
| AC-5 | Manual read of `verification/validation-1.md`'s Git-state paragraph plus `git status --short` re-run fresh | `verification/validation-2.md` |

## Automated verification

Commands that must pass (see `AGENTS.md` "Validation commands"):

```bash
./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
```

```bash
./.venv/Scripts/python.exe -m compileall -q projects shared ui tests campaign_manager.py
```

```bash
git check-ignore -q tests/conftest.py
```

```bash
git ls-files | grep '^keys/'
```

These are the exact commands used throughout this feature
(`verification/validation-1.md`); a Markdown-only change cannot affect their
results, and re-running them after every edit is how that claim is checked
rather than assumed.

## Manual verification

Read every edited file in full and confirm no other document still states or
implies a contradicting rule (see the grep-based checks in the Verification
map). No entry point from `AGENTS.md` §2 is run as part of this.

## Evidence requirements

- Validation record for the final passing cycle (`verification/validation-2.md`,
  which supersedes nothing and stands alongside `validation-1.md`).
- Implementation review with verdict `PASS`.
- This feature never went through `/implement-feature`'s Phase 1, so it has no
  `pre-existing-state-<n>.md` — the `validation-<n>.md` files stand alone as
  this feature's evidence.

## Open questions

| # | Question | Blocking? | Owner | Answer |
|---|---|---|---|---|
| 1 | Should this retroactive spec, once reviewed, be split into two specs matching the two correction rounds, or stay as one covering both? | no | Repo owner | Kept as one spec covering both rounds, since both rounds fix the same workflow documents and splitting after the fact would not change what was built |

`/implement-feature` refuses to start while any **blocking** question is
unanswered. This feature does not invoke `/implement-feature` (retroactive
path), so this is moot here, but is stated for template completeness.

## Retry limit

- Unsuccessful validation-correction cycles before stopping as `blocked`: **5**
- Reviewer `FAIL` → fix rounds before stopping as `blocked`: **3**

## Rollback considerations

Nothing has been committed. Rollback means discarding the uncommitted edits
this feature made: `git restore AGENTS.md CLAUDE.md docs/modernization-log.md`
for the tracked files it touched (note: this would also revert the earlier,
already-uncommitted "loop-engineering setup" edits in those same three files,
since nothing distinguishes them at the working-tree level until a commit
exists), and deleting the untracked files and directories it created —
`features/loop-workflow-consistency/` (including this spec and its
verification files) and, more broadly, `features/QUEUE.md`'s row for this
feature would need manual removal if `features/QUEUE.md` itself is not
restored wholesale. There is no commit to `git revert`.

## Definition of done

- [ ] Every acceptance criterion satisfied, with evidence
- [ ] `python -m pytest -q` and every command under "Automated verification" pass
- [ ] Manual verification completed (or recorded as not required)
- [ ] Verification evidence recorded under `verification/`
- [ ] `feature-reviewer` returned `PASS`
- [ ] No unexplained unrelated changes in `git diff`
- [ ] `docs/code-audit.md` finding status and `docs/modernization-log.md` entry updated in the same change (`AGENTS.md` §7) — no `IH-###` applies; log entry only
- [ ] Queue moved to `human_review` by `/review-feature implementation` on a recorded reviewer `PASS`
- [ ] A **human** moves the queue to `done` after accepting and merging through the normal PR process
