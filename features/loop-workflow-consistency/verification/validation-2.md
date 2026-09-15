# Validation 2 — loop-workflow-consistency — 2026-09-15

Correction round. `verification/validation-1.md` stated the working tree
carried "~57 pre-existing modified files from earlier work" — an
approximation. This record replaces that approximation with an exact,
itemized accounting, run fresh, and then re-runs the four required validation
commands one more time after all of this round's edits. Conventions:
`features/_template/verification/README.md`. `<n>` for this file is `2`
(`validation-1.md` already exists; no `validation-2.md` existed before this
record, per the single numbering rule).

## Fresh `git status --short`, run now

- Command: `git status --short`
- Working directory: repository root
  (`/mnt/c/Users/afif.nahas/Desktop/maddict-data/info-harbor`, a WSL view of
  the Windows checkout)
- Git state: `chore/loop-engineering-setup` @ `0bf25f4`

Complete, exact, current output:

```
 M .claude/agents/data-pipeline-reviewer.md
 M .claude/agents/repository-mapper.md
 M .claude/agents/security-parity-reviewer.md
 M .github/workflows/pr-validation.yml
 M .gitignore
 M AGENTS.md
 M CLAUDE.md
 M README.md
 M README_NEW.md
 M RESTRUCTURE_SUMMARY.md
 M docs/architecture-and-test-environment-plan.md
 M docs/code-audit.md
 M docs/modernization-log.md
 M docs/modernization-spec.md
 M docs/refinement-review.md
 M projects/automation/requirements.txt
 M projects/automation/upload_backend.py
 M projects/campaign-tracker/main.py
 M projects/campaign-tracker/variables.py
 M projects/segments/input.py
 M projects/segments/queries.ini
 M projects/segments/scripts/delete_from_drive.py
 M projects/segments/scripts/push_to_bq.py
 M projects/segments/scripts/transfer_to_drive.py
 M projects/segments/scripts/variables.py
 M pytest.ini
 M requirements-dev.txt
 M shared/config/settings.py
 M tests/conftest.py
 M tests/fakes/fake_bigquery.py
 M tests/fakes/fake_drive.py
 M tests/fixtures/campaign_metadata.py
 M tests/parity/manifest.py
 M tests/parity/test_manifest_helpers.py
 M tests/unit/test_automation_build_query.py
 M tests/unit/test_automation_main_import.py
 M tests/unit/test_automation_requirements.py
 M tests/unit/test_campaign_config.py
 M tests/unit/test_campaign_tracker_import_path.py
 M tests/unit/test_database_loader_segments_characterization.py
 M tests/unit/test_delete_from_drive_safe_default.py
 M tests/unit/test_get_metadata_empty_result.py
 M tests/unit/test_get_run_dates.py
 M tests/unit/test_get_segments_raw_rerun.py
 M tests/unit/test_pipeline_type_mapping.py
 M tests/unit/test_poi_main_import.py
 M tests/unit/test_segments_main_new_import.py
 M tests/unit/test_segments_queries_ini.py
 M tests/unit/test_segments_wrong_campaign_global.py
 M tests/unit/test_shared_config_settings.py
 M tests/unit/test_split_segments_control.py
 M tests/unit/test_ui_add_campaign_response.py
 M tests/unit/test_ui_app_auth.py
 M tests/unit/test_ui_app_safe_defaults.py
 M tests/unit/test_upload_backend_compare_columns.py
 M tests/unit/test_upload_backend_navigate_month.py
 M tests/unit/test_upload_backend_search_files.py
 M ui/app.py
?? .claude/agents/feature-reviewer.md
?? .claude/skills/
?? .codex/
?? docs/PROJECT_STATE.md
?? features/
?? projects/automation/test_backend_upload.py
```

58 `M` lines, 6 `??` lines. Categorized below — every single line above falls
into exactly one bucket.

## Bucket (a) — workflow files intentionally modified by `loop-workflow-consistency`

**3 tracked files** (already `M` above, both rounds combined):

- `AGENTS.md`
- `CLAUDE.md`
- `docs/modernization-log.md`

**Untracked paths this feature owns** (the entire loop-engineering setup
predates this feature's own commit and is itself uncommitted — these are
untracked because nothing on this branch has been committed yet, not because
this feature is hiding anything):

- `docs/PROJECT_STATE.md`
- `features/` (all of it, including this file and the rest of
  `features/loop-workflow-consistency/`)
- `.claude/skills/` (all of it)
- `.claude/agents/feature-reviewer.md`

Total: 3 tracked + 4 untracked path groups = **7 entries** in this bucket.

## Bucket (b) — unrelated pre-existing tracked files, left untouched

**Exact count: 55.** Every other ` M ` line above, listed by name (none of
these were edited, staged, or reverted by this feature, either round):

1. `.claude/agents/data-pipeline-reviewer.md`
2. `.claude/agents/repository-mapper.md`
3. `.claude/agents/security-parity-reviewer.md`
4. `.github/workflows/pr-validation.yml`
5. `.gitignore`
6. `README.md`
7. `README_NEW.md`
8. `RESTRUCTURE_SUMMARY.md`
9. `docs/architecture-and-test-environment-plan.md`
10. `docs/code-audit.md`
11. `docs/modernization-spec.md`
12. `docs/refinement-review.md`
13. `projects/automation/requirements.txt`
14. `projects/automation/upload_backend.py`
15. `projects/campaign-tracker/main.py`
16. `projects/campaign-tracker/variables.py`
17. `projects/segments/input.py`
18. `projects/segments/queries.ini`
19. `projects/segments/scripts/delete_from_drive.py`
20. `projects/segments/scripts/push_to_bq.py`
21. `projects/segments/scripts/transfer_to_drive.py`
22. `projects/segments/scripts/variables.py`
23. `pytest.ini`
24. `requirements-dev.txt`
25. `shared/config/settings.py`
26. `tests/conftest.py`
27. `tests/fakes/fake_bigquery.py`
28. `tests/fakes/fake_drive.py`
29. `tests/fixtures/campaign_metadata.py`
30. `tests/parity/manifest.py`
31. `tests/parity/test_manifest_helpers.py`
32. `tests/unit/test_automation_build_query.py`
33. `tests/unit/test_automation_main_import.py`
34. `tests/unit/test_automation_requirements.py`
35. `tests/unit/test_campaign_config.py`
36. `tests/unit/test_campaign_tracker_import_path.py`
37. `tests/unit/test_database_loader_segments_characterization.py`
38. `tests/unit/test_delete_from_drive_safe_default.py`
39. `tests/unit/test_get_metadata_empty_result.py`
40. `tests/unit/test_get_run_dates.py`
41. `tests/unit/test_get_segments_raw_rerun.py`
42. `tests/unit/test_pipeline_type_mapping.py`
43. `tests/unit/test_poi_main_import.py`
44. `tests/unit/test_segments_main_new_import.py`
45. `tests/unit/test_segments_queries_ini.py`
46. `tests/unit/test_segments_wrong_campaign_global.py`
47. `tests/unit/test_shared_config_settings.py`
48. `tests/unit/test_split_segments_control.py`
49. `tests/unit/test_ui_add_campaign_response.py`
50. `tests/unit/test_ui_app_auth.py`
51. `tests/unit/test_ui_app_safe_defaults.py`
52. `tests/unit/test_upload_backend_compare_columns.py`
53. `tests/unit/test_upload_backend_navigate_month.py`
54. `tests/unit/test_upload_backend_search_files.py`
55. `ui/app.py`

Arithmetic check: 58 total ` M ` lines − 3 workflow-owned tracked files
(bucket a) = **55**, matching the count above and the corrected wording in
`verification/validation-1.md`'s Git-state paragraph.

## Bucket (c) — untracked `.codex/` agent mirrors

- Command: `stat -c '%y %n' .codex/agents/*.toml`
- Working directory: repository root
- Result:

```
2026-08-26 09:10:22.470539200 +0300 .codex/agents/data-pipeline-reviewer.toml
2026-08-26 09:10:22.471539700 +0300 .codex/agents/repository-mapper.toml
2026-08-26 09:10:22.472539100 +0300 .codex/agents/security-parity-reviewer.toml
```

These three files are unrelated Codex tooling mirrors of the pre-existing
`.claude/agents/{data-pipeline-reviewer,repository-mapper,security-parity-reviewer}.md`
specialists (`features/README.md:88-90`; `docs/PROJECT_STATE.md` §8). Their
mtimes (2026-08-26) predate both correction rounds of this feature (2026-09-15)
and match the mtimes recorded in `docs/PROJECT_STATE.md`. Never read or
modified by this feature.

## Bucket (d) — `projects/automation/test_backend_upload.py`

- Command: `stat -c '%y %n' projects/automation/test_backend_upload.py`
- Working directory: repository root
- Result: `2025-12-18 12:57:49.734407300 +0200 projects/automation/test_backend_upload.py`

Untracked. Deletes and recreates a production BigQuery table (IH-042). Must
never be run, imported, edited, deleted, or committed without an explicit
human decision. Not run, imported, edited, deleted, or committed by this
feature. Its mtime (2025-12-18, pre-modernization) is unchanged from the value
recorded in `docs/PROJECT_STATE.md` §8, confirming it was not touched.

## Re-run of the four required validation commands, after all of this round's edits

### Full offline test suite (required, `AGENTS.md` §6)
- Command: `./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`
- Working directory: repository root
- Git state: `chore/loop-engineering-setup` @ `0bf25f4`, not clean (58 pre-existing/self `M` tracked files, 6 untracked paths — see buckets above)
- Exit code: 0
- Result: **278 passed, 17 warnings in 1.74s**
- Relevant output: `278 passed, 17 warnings in 1.74s`
- Pre-existing failure? Not applicable — no failure. **Warning-count
  nondeterminism, reported honestly rather than smoothed over:** this run
  showed 17 warnings; `validation-1.md` observed 17, 18, 19, 18, and 19 across
  five consecutive runs of an unchanged tree, and an earlier run of this same
  command during this round's editing session (after this round's Phase 0
  spec-review-gate edits but before its spec/QUEUE/log edits) showed 18. As
  `validation-1.md` already documented, the *count* of third-party
  deprecation warnings (pyparsing via `httplib2`, `tqdm`'s use of
  `datetime.utcfromtimestamp`) varies run to run because some are only raised
  on a fresh extension-module import; the test count (278), pass/fail result,
  and exit code (0) do not vary. There is no single "true" warning count to
  report — only the range already observed (17–19)

### CI syntax check (`AGENTS.md` §12)
- Command: `./.venv/Scripts/python.exe -m compileall -q projects shared ui tests campaign_manager.py`
- Working directory: repository root
- Git state: `chore/loop-engineering-setup` @ `0bf25f4`, not clean (see above)
- Exit code: 0
- Result: pass, no output (quiet mode compiles everything cleanly)
- Relevant output: none
- Pre-existing failure? Not applicable — no failure

### `tests/` must not be re-ignored (IH-037)
- Command: `git check-ignore -q tests/conftest.py`
- Working directory: repository root
- Git state: `chore/loop-engineering-setup` @ `0bf25f4`, not clean (see above)
- Exit code: 1
- Result: correct — exit 1 means the path is **not** ignored
- Relevant output: none
- Pre-existing failure? Not applicable — exit 1 is the required result

### No credentials tracked
- Command: `git ls-files | grep '^keys/'`
- Working directory: repository root
- Git state: `chore/loop-engineering-setup` @ `0bf25f4`, not clean (see above)
- Exit code: 1 (`grep` found no match)
- Result: correct — nothing printed; no file under `keys/` is tracked
- Relevant output: none
- Pre-existing failure? Not applicable — no match is the required result

## Scope and safety notes

- No entry point from `AGENTS.md` §2 was run; no BigQuery, Drive, or Secret
  Manager call was made; `keys/` was never opened or referenced.
- `.codex/` (bucket c) and `projects/automation/test_backend_upload.py`
  (bucket d) were inspected only with `stat` — never run, imported, edited, or
  deleted — and both still show as untracked in `git status --short` with
  unchanged mtimes.
- No git command that mutates history or the index was run: nothing was
  staged, committed, branched, switched, stashed, pushed, merged, or deleted.
- Every one of the 55 unrelated pre-existing modified tracked files (bucket b)
  is enumerated above and was left byte-for-byte untouched by this feature.
- This evidence contains no secrets, tokens, DIDs, or production data.
