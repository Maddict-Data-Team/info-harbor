---
name: review-feature
description: Adversarial review of one Info-Harbor feature — either its specification before implementation (spec) or its completed implementation (implementation) — delegated to the fresh-context feature-reviewer, with the verdict recorded under the feature's verification directory. Never edits production files and never marks a feature done.
argument-hint: <spec|implementation> <feature-slug> [base-commit]
disable-model-invocation: true
---

# /review-feature

Arguments: `$ARGUMENTS` — mode (`spec` or `implementation`), the feature
slug, and optionally the base commit for an implementation diff.

If the mode or slug is missing, ask for it and stop.

## Never

- Edit, create, or delete files outside `features/<slug>/verification/` and
  the feature's row in `features/QUEUE.md`.
- Fix the problems you find. Report them; the builder or planner fixes them.
- Run an entry point listed in `AGENTS.md` §2, open `keys/`, or contact any
  cloud service.
- Merge, push, deploy, or change branches.
- Set a queue state of `done`. Only a human does that.

## Ownership of the implementation review

The independent implementation review is performed and recorded **only** here,
by `/review-feature implementation <slug>`. `/implement-feature` never invokes
`feature-reviewer` itself, never writes `implementation-review-<n>.md`, and
never sets `human_review` — it stops at `reviewing`. This skill moves a feature
to `human_review` only when **both** hold: the `feature-reviewer` `PASS` it has
just recorded in `features/<slug>/verification/implementation-review-<n>.md`,
**and** a passing latest `features/<slug>/verification/validation-<n>.md`. A
reviewer `FAIL` returns the row to `building`, where the builder re-runs
`/implement-feature <slug>`; after **3** recorded `FAIL` rounds the feature
stops as `blocked` for a human.

## Steps

1. Read `features/QUEUE.md` and confirm `features/<slug>/spec.md` exists. If
   it does not, stop.
2. Determine the review number `<n>` by the single numbering rule in
   `features/_template/verification/README.md`: one more than the highest
   existing `<mode>-review-*.md` for this feature, or `1` when none exists.
   Never overwrite an earlier review record.
3. For **implementation** mode, determine the base commit: the argument if
   given, otherwise the spec's "Base branch" field. Confirm at least one
   `verification/validation-*.md` exists; if none exists, record a `FAIL` for
   "no validation evidence" without delegating, and continue at step 6.
4. Invoke the `feature-reviewer` subagent with the Agent tool
   (`subagent_type: feature-reviewer`). Pass only the mode, the slug, the base
   commit, and the current branch. Do not pass any summary of the work or
   opinion about its quality — the reviewer must form its own.
5. Check the reviewer's first line is exactly `VERDICT: PASS` or
   `VERDICT: FAIL`. If it is neither, treat it as `FAIL` and note the
   malformed output.
6. Write `features/<slug>/verification/<mode>-review-<n>.md` containing:
   - the verdict, date, reviewed branch and commit;
   - **Blocking findings** (must be fixed before progressing);
   - **Non-blocking improvements** (may be deferred; never block a `PASS`);
   - the reviewer's full report, verbatim, below those sections.
7. Update the queue row's Reviewer result column (`PASS`/`FAIL` + review file)
   and status:

   | Mode | Verdict | New status |
   |---|---|---|
   | spec | PASS | unchanged (`ready`) — note "spec review PASS; awaiting human approval" |
   | spec | FAIL | `planning` |
   | implementation | PASS, and latest validation record passed | `human_review` (only this skill may set it) |
   | implementation | PASS, but validation missing or failing | `building` — note the gap |
   | implementation | FAIL | `building`, or `blocked` once this is the third recorded `FAIL` |

8. Report the verdict, blocking findings, non-blocking improvements, the
   evidence file path, and the next action (for `human_review`: a human
   reviews the diff and evidence, then decides whether to merge through the
   normal PR process and set `done`).

End with the `Status / Blockers / Handoff` footer from `AGENTS.md` §8.
