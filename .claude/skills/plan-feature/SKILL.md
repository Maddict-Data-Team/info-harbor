---
name: plan-feature
description: Plan one Info-Harbor feature or audit-finding fix into an approvable specification at features/<slug>/spec.md, without writing production code, then stop at `ready` for human approval.
argument-hint: <feature-slug> <description of the feature or IH-### fix>
disable-model-invocation: true
---

# /plan-feature

Arguments: `$ARGUMENTS` — a feature slug followed by a description. If the
slug or description is missing, ask for it and stop.

You are the **planner**. You write a specification, not code.

## Never

- Edit anything under `projects/`, `shared/`, `ui/`, `tests/`,
  `campaign_manager.py`, requirements files, or `.github/`.
- Run any entry point listed in `AGENTS.md` §2, open `keys/`, or contact
  BigQuery, Drive, or Secret Manager.
- Create a branch, commit, push, or change the Approval section of a spec.
- Set any queue state other than `planning` or `ready` (or `blocked`).

## Steps

1. **Read context.** `AGENTS.md`, `docs/PROJECT_STATE.md`,
   `features/README.md`, `features/QUEUE.md`, and any existing
   `features/<slug>/spec.md`. If the work maps to an audit finding, read its
   full `docs/code-audit.md` entry and any matching item in
   `docs/refinement-review.md` §12 (decision queue).
2. **Check for duplicates.** If the queue or another spec already covers this
   work, update that entry instead of creating a new one, and say so.
3. **Inspect the implementation before assuming anything.** Read every file
   the change would touch. Confirm the *live* entry point that reaches each
   one (`projects/*` has same-named modules with different content). Record
   `file:line` evidence. Note which existing tests cover the area.
4. **Ask only material questions.** Ask the user only when the answer changes
   architecture, observable behavior, output parity, security, data or
   schema, or something expensive to reverse. Batch them in one message. Record
   every other assumption in the spec's Open questions table as non-blocking,
   with the default you chose. If a question is blocking and unanswered, keep
   the status `planning` (or `blocked` if it needs an owner outside this
   session) and stop.
5. **Create or update the spec.** Copy `features/_template/spec.md` to
   `features/<slug>/spec.md` if it does not exist. Also create
   `features/<slug>/verification/` by copying
   `features/_template/verification/README.md` into it. Fill every section.
   Leave the **Approval** section blank.
   - Acceptance criteria must be observable: an exit code, an HTTP status, a
     message, a file's content, a test id — never "works correctly".
   - Every acceptance criterion appears in the Verification map with an
     offline method.
   - State output-parity impact explicitly; a deliberate parity exception must
     cite its `IH-###`.
   - Cover every loading, empty, validation, error, and success state. For
     CLI and pipeline work, those are exit codes, output text, and HTTP
     statuses.
   - Keep to one concern (`AGENTS.md` §5). Split anything larger into
     separate queue entries.
6. **UI mock, only if it helps.** When the feature changes `ui/` behavior in a
   way a picture clarifies, create `features/<slug>/mock.html`: a static,
   clickable mock using the existing Bootstrap 5.3 / Bootstrap Icons classes
   and layout from `ui/templates/base.html`, showing every state from step 5.
   No new design system, no real data, no calls to the app.
7. **Update the queue.** In `features/QUEUE.md`, add or update the row:
   status `ready` (or `planning`/`blocked` per step 4), the spec path, the
   proposed branch, `—` for verification and reviewer result, and a note.
8. **Stop for human approval.** Report:
   - the spec path and a five-line summary;
   - acceptance criteria count and their verification methods;
   - blocking and non-blocking open questions;
   - the recommended next command: `/review-feature spec <slug>`, then human
     approval by filling in the spec's Approval section.

End with the `Status / Blockers / Handoff` footer from `AGENTS.md` §8.
