# Info-Harbor — Project State

**Last audited:** 2026-09-15
**Audited state:** branch `chore/loop-engineering-setup` @ `0bf25f4` — the same commit as, and in sync with, `feature/phase-a-safety-contracts` and `origin/feature/phase-a-safety-contracts` — plus the uncommitted loop-engineering setup described below.
**Method:** Read-only inspection of code, configuration, Git history across every local and remote branch, and all project Markdown, plus an offline test run. No entry point was run, no cloud service was contacted, and `keys/` was not opened.

Confidence labels used below:

- **Fact** — observed directly in code, config, Git, or a command run during this audit.
- **Inference** — a reasoned conclusion from facts, not directly observed.
- **Unverified** — a claim from documentation that this audit could not check.

This file is a snapshot. `docs/code-audit.md` remains the per-defect register and
`docs/modernization-log.md` the chronological record. When they disagree with this
file about an individual finding, re-check the code.

---

## 1. Product summary

Info-Harbor is Maddict's internal marketing-analytics pipeline for location-based
advertising campaigns (Placelift, Placelift Dashboard, Retail, OOH, Comparative
Analysis, and historical-data campaign types). It:

1. records campaign metadata, one row per country, in BigQuery
   `maddictdata.Metadata.Campaign_Tracker` (`projects/campaign-tracker/main.py`;
   `docs/modernization-spec.md` §2);
2. extracts audience segments of device IDs, splits them into served and control
   groups, and publishes them to Google Drive and BigQuery (`projects/segments/`);
3. runs scheduled and manual reporting queries into `Back_End_Footfall` tables and
   imports backend reports from Drive (`projects/automation/`);
4. extracts points-of-interest data (`projects/poi/`);
5. exposes a local Flask operations dashboard over the campaign registry (`ui/app.py`).

**Fact:** the production Cloud Function `ih-cf-executor` is deployed from
`projects/automation` on every push to `main` (`.github/workflows/deploy.yml:1-6,31-37`).

## 2. Current project status

The project is **mid-modernization**. Since 2026-08-19, all work has happened on feature
branches that follow a safety-first, audit-driven process. **None of it has been merged
to `dev` or `main`.**

| Fact | Evidence |
|---|---|
| `main` is still at `c0f2e37`, the pre-modernization baseline; the current branch is 35 commits ahead of it | `git rev-list --left-right --count main...HEAD` → `0 35` |
| The modernization work has split into **two diverged lines** | `git log --graph --all` |
| Line A (this checkout): `feature/safety-test-baseline` → `feature/shared-config-foundation` (`8f35462`) → `feature/phase-a-safety-contracts` (`70f70e8`, `0bf25f4`, both labeled WIP) | `git log --oneline` |
| Line B: `feature/phase2-integration` (`a864c33`) merges the safety baseline, IH-049, and the Phase 2b–2e config migrations of POI, Campaign Tracker, Segments, and Automation, plus IH-050 and IH-051. It exists **locally only** (not on `origin`) and **does not contain Phase A** | `git ls-remote --heads origin` (no match); `git diff --stat HEAD feature/phase2-integration` |
| `feature/automation-shared-config` (`eb7057e`, on origin) has IH-051 rounds 2 and 3, which are **not** in `feature/phase2-integration` | `git log HEAD..feature/automation-shared-config`; the Line B log headings list only IH-051 round 1 |
| This branch's offline suite passes: **278 passed**, 17 deprecation warnings | §10 |
| The latest commit message says the suite "has not been re-run since the trim" and that "the scoped security review has not been run" | `git show 0bf25f4` |

**Inference:** because `main` has none of the fixes, the deployed Cloud Function —
assuming it matches `main`, which is itself unverified (IH-039) — still carries
every defect fixed on these branches.

## 3. Technology stack

| Layer | Technology | Evidence |
|---|---|---|
| Language | Python 3.12 (CI and deploy runtime); local `.venv` is 3.12.4 | `.github/workflows/pr-validation.yml:29`; `deploy.yml:34` (`python312`) |
| Data | Google BigQuery (`google-cloud-bigquery==3.19.0`), SQL templates in `queries.ini` | `requirements.txt`; `projects/automation/queries.ini`; `projects/segments/queries.ini` |
| Files | Google Drive (`google-api-python-client`, `pydrive2`) | `requirements.txt` |
| Secrets | GCP Secret Manager, plus legacy local key files (IH-029) | `requirements.txt`; `docs/code-audit.md` IH-029 |
| Data processing | `pandas==2.1.1`, `tqdm` | `requirements.txt` |
| Web | Flask 3.0.0, Jinja templates, Bootstrap 5.3.0 and Bootstrap Icons 1.10.0 from CDN | `requirements.txt`; `ui/templates/base.html:9,11,278` |
| Runtime | Google Cloud Functions (HTTP trigger, `us-central1`) | `deploy.yml:31-37` |
| Tests | pytest 9.1.1, offline fakes for BigQuery and Drive | `requirements-dev.txt`; `pytest.ini`; `tests/fakes/` |
| CI | GitHub Actions: offline PR validation plus production deploy | `.github/workflows/` |
| Packaging | None (no `pyproject.toml` or `setup.cfg` at the root; `projects/segments/setup.py` exists) | `git ls-files` |

**Not present:** linter, formatter, type checker, end-to-end tests, build step, and
any `.env.example` (`git ls-files`; `find . -name "*.env*"`).

## 4. Architecture summary

| Component | Entry points | Deployed? | Notes |
|---|---|---|---|
| Automation | `projects/automation/main.py` (Cloud Function `main`); `custom_codename.py` via `make custom <code>` | **Yes**, deploy source is this directory only | Loads local modules by explicit path to avoid same-name collisions (`main.py:16-46`, IH-047) |
| Segments | `projects/segments/main.py`, `main_new.py`; `scripts/*.py` | No, run manually | Flat imports plus `sys.path`; `scripts/query_orchestrator.py` and `variables.py` differ from Automation's same-named files |
| Campaign Tracker | `projects/campaign-tracker/main.py`, `main_new.py` | No, run manually | Hyphenated directory; loaded through `shared/utils/compatibility.py` (IH-014) |
| POI | `projects/poi/main.py` | No, run manually | IH-036: needs validation |
| Flask UI | `ui/app.py` (`127.0.0.1:5000`, `debug=False`, `ui/app.py:481`) | No | 13 routes; the 5 state-changing routes require a bearer token (`ui/app.py:186-364`) |
| CLI | `campaign_manager.py` (`list`, `show`, `segments`, `tracker`, `automation`, `validate`) | No | `campaign_manager.py:167-188` |
| Shared | `shared/config/settings.py` (unconsumed here); `campaigns/` registry and `database_loader.py`; `models/campaign.py`; Phase A contracts | Not in the deploy artifact | `deploy.yml` uploads only `projects/automation` (IH-050 context) |
| Tests | `tests/unit`, `fakes`, `fixtures`, `parity` | No | `tests/conftest.py:48-83` blocks real Google client constructors |

The target architecture (`apps/`, `packages/infoharbor_core/`, `deploy/`) is accepted
but not yet built (`docs/architecture-and-test-environment-plan.md` §Target repository structure).

## 5. Implemented features

"Implemented" means the code exists and its offline-testable parts are tested. **No
production behavior was verified in this audit.**

- **Scheduled reporting pipeline** — status transitions, active-campaign selection,
  backend-report import, `queries.ini` reporting (`projects/automation/main.py`,
  `query_orchestrator.py`, `upload_backend.py`; `docs/modernization-spec.md` §1.3).
  Offline tests: `test_get_run_dates.py`, `test_automation_build_query.py`,
  `test_pipeline_type_mapping.py`, `test_upload_backend_*.py`.
- **Manual reporting run** by code name (`custom_codename.py`, `Makefile:21-24`).
- **Campaign metadata creation** (`projects/campaign-tracker/main.py`); `main_new.py` is importable since IH-014.
- **Segment extraction, split, and publication** (`projects/segments/`). Served and
  control groups are disjoint since IH-007, small pools no longer crash since IH-008,
  and reruns truncate since IH-009 (`test_split_segments_control.py`, `test_get_segments_raw_rerun.py`).
- **POI extraction** (`projects/poi/`). Only an import smoke test exists (`test_poi_main_import.py`).
- **Flask operations UI** with interim bearer-token auth and a fail-closed secret key
  (IH-025, IH-027; `test_ui_app_auth.py`, `test_ui_app_safe_defaults.py`).
- **Campaign registry and CLI** (`shared/config/campaigns/`, `campaign_manager.py`; `test_campaign_config.py`).
- **Backend-report CSV column validation** (`upload_backend.compare_columns`; `test_upload_backend_compare_columns.py`).
- **Offline safety net** — 278 tests, fakes, parity hash helpers, and non-deploying PR CI
  (`tests/`, `.github/workflows/pr-validation.yml`).
- **Shared settings foundation** (`shared/config/settings.py`; `test_shared_config_settings.py`) — imported by no entry point on this branch.
- **Phase A safety contracts** — `shared/config/environment.py`, `source_allowlist.py`,
  `output_policy.py`. Imported by no live entry point and not enforced at runtime
  (checked by grep during this audit; enforced by
  `test_environment_contract.py::TestPhaseAModulesAreAdditiveAndUnimported` per the modernization log).

## 6. Partially implemented features

| Item | What exists | What is missing | Evidence |
|---|---|---|---|
| Phase A contracts | 3 of the 4 planned contracts, with passing tests | Redaction contract (deferred); the scoped security review was never run; the commits are labeled WIP | `docs/modernization-log.md` 2026-09-08 entry; `git show 0bf25f4` |
| Config unification (IH-048, Phases 2b–2e) | Foundation on this line; all four migrations on Line B | Integration of the two lines; Line B lacks IH-051 rounds 2–3; migrations not verified in this audit | §2 |
| IH-012 tracker insert | `.result()` added so a failed insert raises | `id` assignment race | `docs/code-audit.md` IH-012 |
| IH-028 `delete_from_drive.py` | `DELETE_MODE = False` default (`delete_from_drive.py:37`) | `--confirm` flag; required folder-id argument (still hardcoded at `:31`) | IH-028 |
| IH-025 UI auth | Bearer token on 5 routes | CSRF protection, per-user identity, rotation. The two HTML-form routes return 401 from their own forms | `docs/refinement-review.md` §5 |
| `/api/campaigns/add` | Validates input, returns an honest 501 | Persistence | IH-041 |
| Parity harness | Hash helpers, tested in isolation | End-to-end fixture runs | `docs/modernization-spec.md` §7 |
| POI module | Code and import smoke test | Write-correctness validation; CI or ownership decision | IH-036 |

## 7. Planned features (not implemented)

From `docs/architecture-and-test-environment-plan.md` (Phases B–F) and
`docs/modernization-spec.md` §3 and §8:

- **Phase B** — wire the refusal gates into client creation and write paths (explicit approval required).
- **Phase C** — test GCP project, test Drive root, identity, staging TTL, and `Campaign_Runs_test` (cloud writes; separate approval).
- **Phase D** — per-application migration with a manual test-environment smoke test.
- **Phase E** — shared-core packaging for the Cloud Function.
- **Phase F** — `feature → dev → main` release discipline.
- **Shared run-service core** (`runners/core.py` + `RunPolicy`) and the `Campaign_Runs` audit table.
- **Structured redacted logging**, and a **CI test gate before deploy** (IH-034).
- **Removal of `get-pip.py` and `aaa`** once IH-039 is resolved.

## 8. Current uncommitted work

| Path | Origin | Assessment |
|---|---|---|
| `projects/automation/test_backend_upload.py` (untracked, mtime 2025-12-18) | Pre-modernization manual script (IH-042) | **Hazard.** Its `main()` **deletes and recreates** production BigQuery table `Back_End_Reports.173` using Secret Manager credentials (`test_backend_upload.py:39-51,145-156`). pytest does not collect it (`pytest.ini` `testpaths = tests`), but `python -m pytest projects/` would try to import it. Left untouched; needs a human decision |
| `.codex/agents/*.toml` (untracked, 2026-08-26) | Codex mirrors of the three `.claude/agents` definitions; `tests-output/codex-pytest-20260826/` suggests a Codex test run the same day (inference) | Content matches the Claude agent bodies. Commit or ignore is a human decision |
| Loop-engineering setup (this audit), and the loop workflow consistency fixes that followed it | See the modernization log entries of 2026-09-15 | Uncommitted, but no longer riding along with Phase A: the branch `chore/loop-engineering-setup` @ `0bf25f4` exists and holds this work. What remains is human review and then a commit on that branch — see §15 |

Stashes: `stash@{0}` and `stash@{1}` are both on `main` from 2025. `docs/refinement-review.md` §1 mentions
5 stashes, which suggests that checkpoint was made in a different clone (inference; the
2026-08-19 log entry records work in a sibling clone). All were left untouched.

## 9. Known bugs and technical debt

### Open or unresolved audit findings (`docs/code-audit.md`)

- **Critical:** IH-001 (segments can publish under the wrong campaign), IH-002 (bare `except` plus an always-200 Cloud Function), IH-004 (DB-loaded campaigns lose segments).
- **High:** IH-003, IH-006, IH-010, IH-011, IH-018, IH-030, IH-031, IH-034.
- **Medium or Low:** IH-019, IH-020, IH-029, IH-032; In Progress: IH-012, IH-028, IH-048; Needs Validation: IH-036, IH-039, IH-040, IH-042.
- The decision owners and options for each are in `docs/refinement-review.md` §12.

### Candidate findings from this audit (not yet registered)

These have no `IH-###` IDs yet. Lines A and B have already allocated IDs independently
(Line B uses IH-049 to IH-051), so new IDs should be assigned after the lines are
integrated to avoid collisions.

1. **This branch does not pin `numpy`** (`requirements.txt`, `projects/automation/requirements.txt`),
   but IH-049's fix exists only on `fix/numpy-pandas-compat` and Line B. A fresh CI
   install on this branch may resolve numpy 2.x against `pandas==2.1.1`, per IH-049's
   own analysis. **Unverified:** CI results could not be read because `gh` is not installed.
   The local `.venv` has `numpy 1.26.4`, which is why local tests pass.
2. **The documented `python -m pytest -q` fails with the system interpreter** on this
   machine (`ModuleNotFoundError: No module named 'pytest'`). It only works through
   `.venv/Scripts/python.exe`.
3. **Stray tracked files:** `aaa` (IH-039); `run_report.csv` (tracked since `8981f83`,
   which lists production Drive file IDs and column-mismatch results, apparently output
   of `data_validation.py` — inference); `get-pip.py` is tracked even though
   `.gitignore:23` ignores it.
4. **`git diff --check main...HEAD` reports 973 "trailing whitespace" lines.** Most
   likely CRLF artifacts (`core.autocrlf=true`; `README.md` has mixed CRLF and LF), not
   real whitespace (inference).
5. **`CLAUDE.md`'s syntax-check command omitted `tests` and `campaign_manager.py`** compared
   with CI (`pr-validation.yml:58`). Corrected in this setup.

## 10. Validation commands

Recorded on 2026-09-15 against `0bf25f4` before any setup file existed. Setup files
are Markdown only and cannot affect these results.

| Command | Result | Blocks feature work? |
|---|---|---|
| `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | **Exit 0 — 278 passed**, 17 warnings (third-party deprecations: pyparsing via httplib2, and `datetime.utcfromtimestamp` in tqdm) | No |
| `python -m pytest ...` (system Python 3.12.4) | **Fails** — `No module named 'pytest'` (pre-existing environment state) | No, if `.venv` is used |
| `.venv/Scripts/python.exe -m pytest --collect-only -q` | 278 tests collected | — |
| `.venv/Scripts/python.exe -m compileall -q projects shared ui tests campaign_manager.py` (CI command) | Exit 0 | No |
| `git check-ignore -q tests/conftest.py` | Exit 1 (not ignored — correct, IH-037) | No |
| `git ls-files \| grep -c '^keys/'` | `0` | No |
| `git diff --check main...HEAD` | 973 trailing-whitespace reports (see §9 item 4) | No |
| Lint, format, type-check, end-to-end, build | **Not configured** | Not blocking; do not add casually |
| CI status (`gh run list`) | **Not available** — `gh` is not installed | Unknown; see §9 item 1 |

Setup for a fresh machine: create a virtualenv, then
`pip install -r requirements.txt -r requirements-dev.txt` from PyPI only. Pin `numpy<2`
until IH-049 is integrated (`docs/modernization-log.md` 2026-08-19 records this workaround).

## 11. External services and deployment state

| Service | Use | Evidence |
|---|---|---|
| GCP project `maddictdata` | Production source and output data | `docs/architecture-and-test-environment-plan.md` §Test environment boundary |
| BigQuery | `Metadata.Campaign_Tracker`, `Back_End_Footfall.*`, `Back_End_Reports.*`, `Placelift_Campaign_Segments.*`, `POI_DB_*`, `Location_Signals`, `Automated_HWG`, `Lookups` | Same document, §Static BigQuery inventory |
| Google Drive | Segment CSVs (`Year/Quarter/Campaign`), backend reports | `docs/modernization-spec.md` §1.2–1.3 |
| Secret Manager | Cloud Function credentials | `projects/automation/main.py:9,48-51` |
| Cloud Function `ih-cf-executor` | `us-central1`, `python312`, HTTP trigger, service account `dev-cloud-function-2024@maddictdata.iam.gserviceaccount.com`, deployed with `secrets.GCP_SA_KEY` | `deploy.yml` |
| Test GCP project | **Does not exist yet** (placeholder `<GCP_TEST_PROJECT_ID>`) | Architecture plan §Open decisions |

Deploy gate: none. A push to `main` deploys (IH-034). Whether the deployed function
matches `main` is **unverified** (IH-039).

## 12. Confirmed decisions

| Decision | Source |
|---|---|
| Never commit to `main`; one concern per feature branch; ask before branching, committing, or pushing | `AGENTS.md` §3, §5 |
| No production cloud access and no `keys/` access by agents | `AGENTS.md` §2 |
| Preserve output parity except for approved, cited bug fixes | `AGENTS.md` §4; `docs/modernization-spec.md` §6 |
| Keep one repo, keep Flask as the operations app, `dev` is the integration branch and `main` is release | Architecture plan §Decisions |
| Small-pool control group is 50% of the eligible pool (interim, pending methodology owner) | `README.md` Modernization Status, 2026-08-20 |
| Interim bearer-token UI auth; `INFO_HARBOR_API_TOKEN` and `INFO_HARBOR_FLASK_SECRET_KEY` are required | `README.md`; IH-025, IH-027 |
| New shared settings live in `shared/config/settings.py`, not `base_config.py` (import side effects) | Modernization log 2026-08-21 |
| Phase A redaction is deferred to the observability phase | Modernization log 2026-09-08 |
| Phase A contracts stay unwired; Phase B needs explicit approval | `CLAUDE.md`; architecture plan §Phase A |
| Finding-less capability work needs a log entry only, with no invented `IH-###` | `CLAUDE.md` |
| Loop-engineering workflow: `features/` + `/plan-feature`, `/implement-feature`, `/review-feature` + `feature-reviewer` | This setup; `AGENTS.md` §18–22 |

## 13. Open decisions

| # | Decision | Blocking? | Owner |
|---|---|---|---|
| D1 | **Integration order of Line A (Phase A) and Line B (Phase 2 migrations, IH-049–051)**, and which base branch new features start from | Blocks Phase B and choosing a base branch for new feature branches. Does not block this setup | Developer / repo owner |
| D2 | Keep and push the local-only `feature/phase2-integration`, or rebuild it from origin branches (it lacks IH-051 rounds 2–3) | With D1 | Developer |
| D3 | Merge `feature/safety-test-baseline` (human checkpoint pending since 2026-08-20) | Yes, for release | Repo owner |
| D4 | Reword or squash the WIP commits `70f70e8` and `0bf25f4` before any PR | No | Developer |
| D5 | Disposition of `projects/automation/test_backend_upload.py` (IH-042) | No | Developer who knows its history |
| D6 | Commit `.codex/agents/*.toml`, and whether Codex needs mirrors of the loop skills | No | Repo owner |
| D7 | Decision queue items IH-001, 002/003, 004, 006, 010, 011, 018–020, 029, 030, 031/032, 034, 036, 039, 040, 012-residual, 028-residual | Per item | See `docs/refinement-review.md` §12 |
| D8 | Phase C prerequisites: test project ID, `<code>_streach` producer, test Drive root and retention, Power BI strategy | Blocks Phase C | GCP owner |
| D9 | How the two HTML-form routes will send the bearer token (IH-025 consequence) | No | Developer / UI owner |

## 14. Documentation conflicts

| Document | Claim | Reality (evidence) | Action taken |
|---|---|---|---|
| `README.md` Modernization Status | "Current phase: Phase 2 … 103 tests … 46 findings", last updated 2026-08-21 | 278 tests on this branch; Phase A added; Phase 2 migrations on another line; 48 index entries here and 51 on Line B | Outdated-snapshot note added pointing here |
| `README.md` Installation, Usage, Env vars | `cd ui; python app.py`; set `GOOGLE_CLOUD_PROJECT`, `BIGQUERY_DATASET`, `API_KEYS_PATH`; `ui/static/`; Google Ads and Facebook APIs | The app refuses to start without `INFO_HARBOR_FLASK_SECRET_KEY` (IH-027); those three env vars are read nowhere (grep); no `ui/static` is tracked; no Ads or Facebook code (grep). Running `ui/app.py` is also prohibited for agents (`AGENTS.md` §2) | Covered by the same note |
| `README_NEW.md`, `RESTRUCTURE_SUMMARY.md` | Restructure "complete and ready for production", "100% backward compatibility", `test_paths.py` passes | `test_paths.py` does not exist; `main_new.py` files were broken until IH-014 and IH-015; DB-loaded campaigns lose segments (IH-004) | Marked superseded, content preserved |
| `docs/architecture-and-test-environment-plan.md` | "Status: implementation has not started" | Phase A contracts implemented (`70f70e8`, `0bf25f4`) without redaction | Status line updated |
| `docs/modernization-spec.md` | §1.1 `main_new.py` fails (IH-014); §1.5 no authentication; §9 50 tests | IH-014 and IH-025 are fixed; 278 tests | Historical-baseline note added |
| `docs/code-audit.md` IH-048 | Progressed by "uncommitted working tree pending review" | Committed as `8f35462` | Corrected |
| `docs/refinement-review.md` | 5 stashes present; 97 tests | 2 stashes in this clone; 278 tests now | Left as is (dated checkpoint) |
| `docs/modernization-log.md` Phase A entry | Dated 2026-09-08 | Commits dated 2026-09-09 | Left as is (one-day difference, likely drafted the day before) |
| `CLAUDE.md` here vs. on Line B | This branch has Common commands, Conventions, and Architecture map sections | Line B's `CLAUDE.md` lacks them | Recorded for D1 merge |
| `projects/campaign-tracker/README.md` | Run `main.py` after editing `input.py` | Still accurate for humans; agents must not run it | None |

## 15. Recommended next feature or repair

**Before any feature loop (human, about 5 minutes):**

1. **Done:** this setup no longer rides along with Phase A. It sits on its own branch,
   `chore/loop-engineering-setup` @ `0bf25f4` (the same commit as
   `feature/phase-a-safety-contracts`), where it is still uncommitted. What remains is to
   review the setup files and commit them on that branch.
2. Decide D1, the base branch.

**First controlled Level-1 loop: `ih-028-delete-from-drive-confirm`** — complete IH-028
by adding a required `--confirm` flag and a required folder-id argument to
`projects/segments/scripts/delete_from_drive.py`.

Why it fits a first loop:

- **One file, one concern.** `delete_from_drive.py` currently has no argument parsing
  (`:282-319`) and a hardcoded folder ID (`:31`). The file is identical on Lines A and B,
  so the D1 outcome does not change the code.
- **Owner already decided:** "Cheap follow-up, low risk … Who decides: Developer"
  (`docs/refinement-review.md` §12, IH-028 residual).
- **No production output or parity change.** It only changes the CLI of a script operators run by hand.
- **Offline-testable** by extending the existing AST test pattern
  (`tests/unit/test_delete_from_drive_safe_default.py`) or by testing a pure argument
  parser, without importing Drive clients or running the script.
- **Safety value** — it closes the remaining gap on a script that permanently deletes Drive files.
- **Exercises the whole loop:** spec with error and validation states (missing flag,
  missing folder ID), acceptance criteria mapped to tests, docs update, reviewer.
