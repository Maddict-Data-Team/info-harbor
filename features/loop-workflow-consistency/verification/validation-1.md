# Validation 1 — loop-workflow-consistency — 2026-09-15

Markdown-only change to the loop-engineering workflow documents. No Python,
YAML, or configuration file was touched, so no behavior and no output parity
is affected. Conventions: `features/_template/verification/README.md`.

**Git state for every record below:** `chore/loop-engineering-setup` @
`0bf25f4`; working tree **not clean** — the working tree also carries 55
pre-existing modified tracked files from earlier, unrelated work (exact,
itemized list: `verification/validation-2.md`), plus the untracked
loop-engineering setup (`.claude/agents/feature-reviewer.md`, `.claude/skills/`,
`docs/PROJECT_STATE.md`, `features/`), and the untracked, untouched `.codex/`
and `projects/automation/test_backend_upload.py`. None of those pre-existing
changes were edited, staged, or reverted by this change.

**Commands run after all edits were complete**, from the repository root
(`/mnt/c/Users/afif.nahas/Desktop/maddict-data/info-harbor`, a WSL view of the
Windows checkout). Baseline recorded on this branch before the edits:
278 passed, 17 warnings, exit 0; `compileall` exit 0
(`docs/PROJECT_STATE.md` §10).

### Full offline test suite (required, `AGENTS.md` §6)
- Command: `./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`
- Working directory: repository root
- Git state: `chore/loop-engineering-setup` @ `0bf25f4`, not clean (see above)
- Exit code: 0
- Result: **278 passed** — the same pass count and exit code as the pre-change
  baseline. Run five times over this unchanged working tree
- Relevant output: `278 passed, 17 warnings in 1.59s`, then `278 passed, 18
  warnings`, `278 passed, 19 warnings`, `278 passed, 18 warnings`, `278 passed,
  19 warnings`
- Pre-existing failure? Not applicable — no failure. **Observed
  nondeterminism, reported rather than smoothed over:** the *warning count*
  varies between 17 and 19 across identical runs of the same unchanged tree.
  The test count, results, and exit code do not vary. Every warning is a
  third-party deprecation — `PyparsingDeprecationWarning` from
  `httplib2/auth.py`, `datetime.utcfromtimestamp` in `tqdm/std.py`, and
  protobuf `PyType_Spec` warnings raised at `<frozen importlib._bootstrap>:488`.
  The last group only appears when the extension module is imported fresh,
  which is what makes the total vary. This is pre-existing environment
  behavior; a Markdown-only change cannot affect it. The "17 warnings" in
  `docs/PROJECT_STATE.md` §10 is therefore one observation of a varying number,
  not a stable invariant

### Documented `python -m pytest -q` with the system interpreter
- Command: `python3 -m pytest -q`
- Working directory: repository root
- Git state: `chore/loop-engineering-setup` @ `0bf25f4`, not clean (see above)
- Exit code: 1
- Result: fails to start — `/usr/bin/python3: No module named pytest`
- Relevant output: `/usr/bin/python3: No module named pytest`
- Pre-existing failure? **Yes — pre-existing environment state, not caused by
  this change.** `docs/PROJECT_STATE.md` §9 item 2 and §10 already record that
  the documented `python -m pytest -q` only works through
  `.venv/Scripts/python.exe` on this checkout. The interpreter reached here is
  the WSL Linux `/usr/bin/python3`, which has no pytest installed; the Windows
  `.venv` interpreter is the supported one (`CLAUDE.md` "Common commands")

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
  Manager call was made; `keys/` was never opened.
- `projects/automation/test_backend_upload.py` (IH-042) and `.codex/` were left
  untouched — both still show as untracked in `git status --short`.
- No git command that mutates history or the index was run: nothing was staged,
  committed, branched, switched, stashed, pushed, merged, or deleted.
- This evidence contains no secrets, tokens, DIDs, or production data.
