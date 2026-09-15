# Feature Queue

Single source of truth for loop state. Rules and state definitions:
`features/README.md`. Current-state evidence: `docs/PROJECT_STATE.md`.

States: `idea` · `planning` · `ready` · `building` · `reviewing` ·
`human_review` · `done` · `blocked`

Only a human sets `done`. `ready` means "awaiting human approval", not
"approved".

**Populated 2026-09-15 from repository evidence.** Historical work that predates
this workflow has no `features/<slug>/spec.md` and has never been reviewed by
`feature-reviewer`, so none of it is marked `done` or `human_review`.

## Active and historical work

| Feature | Status | Specification | Branch | Verification | Reviewer result | Notes |
|---|---|---|---|---|---|---|
| Loop-engineering setup | `reviewing` | — (this setup task) | uncommitted on `chore/loop-engineering-setup` @ `0bf25f4` (branched from the Phase A tip; the same commit as `feature/phase-a-safety-contracts`) | `docs/PROJECT_STATE.md` §10: 278 passed before the change; Markdown-only change | Not reviewed (`feature-reviewer` did not exist before this change) | The branch move is done. Remaining: human review of the setup files, then a commit on this branch |
| Loop workflow consistency fixes | `reviewing` | `features/loop-workflow-consistency/spec.md` (retroactive — written after the fixes were already made) | `chore/loop-engineering-setup` @ `0bf25f4` (uncommitted) | `features/loop-workflow-consistency/verification/validation-1.md`, `validation-2.md` | pending independent review | Markdown-only: one evidence-numbering rule, one owner of the implementation review and of `human_review`, stale branch/state corrections, a spec-review gate before `/implement-feature`, and an exact (not approximate) pre-existing-file count. Log entries: `docs/modernization-log.md` 2026-09-15 (both rounds). Next: `/review-feature spec loop-workflow-consistency`, then `/review-feature implementation loop-workflow-consistency` — no `/implement-feature`, per the Phase A retroactive-spec precedent (the “Phase A safety contracts” row below) |
| Safety test baseline + Phase 4 fixes (IH-005…IH-047) | `blocked` | — (legacy checkpoint: `docs/refinement-review.md`) | `feature/safety-test-baseline` @ `545852d` (on origin) | 97 passed recorded there; its tests are ancestors of the 278 passing on Line A | Legacy `data-pipeline-reviewer` and `security-parity-reviewer` passes (§8 of that doc), not a loop `PASS` | Blocked on human merge decision (D3), pending since 2026-08-20. Not on `dev` or `main` |
| Shared settings foundation (IH-048) | `blocked` | — (legacy: modernization log 2026-08-21) | `feature/shared-config-foundation` @ `8f35462` (on origin; included in Line A) | `test_shared_config_settings.py` passes within the 278 run of 2026-09-15 | None | Blocked on D1/D3 integration. Audit entry's "uncommitted" note corrected |
| Phase A safety contracts | `reviewing` | — (legacy: `docs/architecture-and-test-environment-plan.md` §Phase A) | `feature/phase-a-safety-contracts` @ `0bf25f4` (on origin) | 278 passed on 2026-09-15 (`docs/PROJECT_STATE.md` §10) | **Not run** — `0bf25f4` says the scoped security review was never run | 2 WIP commits (D4). Redaction deferred by decision. Next: retroactive spec, then `/review-feature implementation` |
| Phase 2b–2e config migrations + IH-049/050/051 | `blocked` | — (legacy: Line B modernization log) | `feature/phase2-integration` @ `a864c33` (**local only**); origin `feature/{poi,campaign-tracker,segments,automation}-shared-config`, `fix/numpy-pandas-compat` | Not verified in this audit (needs a checkout) | Legacy security reviews recorded under IH-050 and IH-051 | Diverged from Phase A (D1, D2). Lacks IH-051 rounds 2–3 (`eb7057e`). Carries the numpy pin this branch may need in CI |

## Candidate work

| Feature | Status | Specification | Branch | Verification | Reviewer result | Notes |
|---|---|---|---|---|---|---|
| `ih-028-delete-from-drive-confirm` — required `--confirm` flag and folder-id argument | `idea` | — | proposed `fix/ih-028-delete-from-drive-confirm` | — | — | **Recommended first Level-1 loop** (`docs/PROJECT_STATE.md` §15). Developer-owned decision; offline-testable; no parity change |
| IH-042 — disposition of untracked `projects/automation/test_backend_upload.py` | `blocked` | — | — | — | — | Human decision (D5). The script deletes and recreates a production BigQuery table; never run it |
| IH-049 on Line A — numpy pin for CI | `blocked` | — | fix exists on `fix/numpy-pandas-compat` | — | — | Resolve through D1 rather than re-implementing. CI breakage on Line A is unverified |
| IH-001 — segments query builder uses a stale global campaign | `idea` | — | — | Characterization: `test_segments_wrong_campaign_global.py` | — | Critical. Decision queue recommends option (a); needs its own branch |
| IH-012 residual — single multi-row tracker `INSERT` | `idea` | — | — | — | — | Developer decision; changes `id` values |
| IH-025 follow-up — HTML forms cannot send the bearer token | `idea` | — | — | — | — | Needs a UI and auth decision (D9) |
| Phase A redaction contract | `idea` | — | — | — | — | Deferred to the observability phase by decision |
| IH-030 — escape or parameterize SQL and Drive query strings | `idea` | — | — | — | — | High. Decision queue recommends Drive escaping first |
| IH-002 + IH-003 — truthful failures + `Campaign_Runs` | `blocked` | — | — | — | — | Needs infrastructure owner design decision |
| IH-004 — DB-loaded campaigns lose segments | `blocked` | — | — | Characterization test exists | — | Needs field-precedence decision |
| IH-006 — `Retail Intelligence Dashboard` naming | `blocked` | — | — | — | — | Needs naming owner |
| IH-018 / IH-019 / IH-020 — reporting window and dedupe semantics | `blocked` | — | — | — | — | Needs placelift methodology owner |
| IH-034 — test gate before production deploy | `blocked` | — | — | — | — | Deployment configuration; needs infrastructure owner approval |
| Phase B — wire refusal gates into entry points | `blocked` | — | — | — | — | Needs explicit approval and D1 |
| IH-010, IH-011, IH-029, IH-031, IH-032, IH-036, IH-039, IH-040 | `blocked` | — | — | — | — | Each needs the decision, access, or owner listed in `docs/refinement-review.md` §12 |
