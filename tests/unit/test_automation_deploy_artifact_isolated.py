"""
IH-050/IH-051 (both found by security review of Phase 2e / IH-048's
Automation migration, before that change was committed):

IH-050 (fixed): `.github/workflows/deploy.yml` deploys the Cloud Function
via `gcloud functions deploy ... --source projects/automation`, which
uploads ONLY that directory. Phase 2e's first version made
`projects/automation/variables.py` import `shared.config.settings`
unconditionally, which lives outside `projects/automation/` -- that import
would fail in the deployed artifact, which never contains `shared/` at
all.

IH-051, round 1 (superseded by round 2 below): IH-050's own remedy --
computing a repository root and inserting it into `sys.path`, then `from
shared.config import settings` -- reintroduced a subtler problem. That's
still a name-based import of the generic package name
`shared.config.settings`, which Python's import machinery resolves
against WHATEVER is on `sys.path`, not necessarily this repository's own
file. Fixed by never mutating `sys.path` and never importing
`shared.config.settings` by name at all -- `variables.py` instead
computed its own expected canonical file path directly
(`<candidate_root>/shared/config/settings.py`, derived from
`variables.py`'s own `__file__`) and loaded whichever file actually
existed there via `importlib.util.spec_from_file_location`.

IH-051, round 2 (superseded by round 3 below): round 1 still trusted "two
parents above this file" as this repository's root merely because *some*
file existed at the computed `shared/config/settings.py` path. In the
deployed, flattened Cloud Function artifact, "two parents above
`__file__`" is an AMBIENT HOST PATH with no relationship to this
repository -- if anything (the runtime, a build layer, an unrelated
package) happens to place a `shared/config/settings.py`-shaped file at
that ambient location, round 1's logic would silently trust it. Fixed by
adding a structural precondition: this file's own location must actually
match the real repository's shape
(`<candidate_root>/projects/automation/variables.py`, verified both
syntactically and by `os.path.samefile` resolution) before the canonical
file at that candidate root is trusted at all.

IH-051, round 3 (fixed here): round 2's exact-layout + samefile checks
are necessary but NOT sufficient -- they only prove this file sits at the
*relative path* `projects/automation/variables.py` below the candidate
root, not that the candidate root is genuinely a checkout of this
repository at all. A deployed artifact placed at
`<ambient_root>/projects/automation/variables.py` (matching that exact
expected shape) would satisfy round 2's checks completely while
`<ambient_root>` is still not this repository -- a fake
`<ambient_root>/shared/config/settings.py` would then be trusted. Fixed
by requiring `<candidate_root>/.git` to exist (a real-checkout marker --
`os.path.exists()`, not `os.path.isdir()`, since a normal clone has
`.git` as a directory but a git worktree has it as a plain file
containing a `gitdir: <path>` pointer) as one more required precondition.
A real deployment artifact never carries repository metadata for an
ambient two-parents-up directory to coincidentally or deliberately
satisfy, so this closes the gap for the actual threat model without
trying to fully authenticate repository identity.

Offline tests that import from a full repository checkout (as every other
test in this suite does) cannot detect any of this on their own: the repo
root is already on `sys.path` there for unrelated reasons
(`tests/conftest.py`), so `shared` is always importable in that process
regardless of what a real deploy artifact would contain, this file's own
real location always genuinely matches the repository's shape there, and
the real repository checkout genuinely has a `.git` directory.

This file proves, in order:

1. `_shared_config_fallback.py`'s values never drift from
   `shared/config/settings.py`'s (`TestFallbackMatchesSharedSettings`).
2. An isolated copy of exactly what `--source <dir>` (read from
   `.github/workflows/deploy.yml` itself, not hardcoded) would upload --
   built from the real files on disk, excluding only `__pycache__` and
   files not tracked by git (which a real CI checkout, and therefore a
   real deploy, would never contain either) -- still imports
   `variables.py` and `main.py` correctly, through the fallback path,
   with `shared` genuinely unimportable (`TestIsolatedDeployArtifact`).
3. A full repository checkout resolves `variables.py`'s settings to the
   exact canonical `shared/config/settings.py` file (by `__file__`, not
   just by value), while the isolated deploy copy resolves to its own
   bundled fallback file -- proving the *selection*, not just the
   resulting values (`TestCanonicalVsFallbackSelection`).
4. Neither context can be hijacked by an unrelated, conflicting
   `shared.config.settings` placed elsewhere on `sys.path`/`sys.modules`
   (`TestConflictingSharedPackageIsIgnored`).
5. A fake `shared/config/settings.py` planted at the EXACT flat ambient
   candidate path a flattened deployment artifact would compute still
   loses to the bundled fallback -- the IH-051 round 2 regression test
   (`TestAmbientCanonicalPathIsNotTrusted`).
6. A fake `shared/config/settings.py` planted at the candidate root of a
   deployment artifact that IS nested exactly like a real checkout
   (`<ambient_root>/projects/automation/variables.py`) but has no `.git`
   marker still loses to the bundled fallback -- the IH-051 round 3
   regression test (`TestNestedAmbientRootWithoutGitMarkerIsNotTrusted`).

No test here constructs a real Google client or touches network/
credentials: variables.py only imports `bigquery` for `SchemaField`
objects (plain data classes), never a client; main.py's `main()`/
`query_bigquery_and_process()` are never called.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import textwrap

import pytest


def _deploy_source_relpath(repo_root) -> str:
    """Read the actual `--source` argument out of
    .github/workflows/deploy.yml instead of hardcoding
    "projects/automation" -- if that workflow ever changes what
    directory it deploys, this test starts covering the wrong directory
    loudly (via this assertion / a changed result) rather than silently
    continuing to check a stale, hardcoded path."""
    deploy_yml_path = repo_root / ".github" / "workflows" / "deploy.yml"
    deploy_yml = deploy_yml_path.read_text(encoding="utf-8")
    match = re.search(r"--source[ \t]+(\S+)", deploy_yml)
    assert match, (
        f"expected to find a --source argument in {deploy_yml_path} -- "
        f"if this workflow's deploy command changed shape, update this "
        f"regex to match, don't just hardcode a path around it"
    )
    return match.group(1)


def _build_isolated_deploy_copy(repo_root, dest_dir):
    """Copy exactly what a real `gcloud functions deploy --source
    <dir>` (dir read from deploy.yml itself) would upload from this
    working tree: every file under that directory that is tracked by
    git (a real deploy runs from a `git checkout`, not this machine's
    local working tree, so an untracked file here -- e.g. a stray local
    test fixture -- would never reach a real deploy either), minus
    __pycache__/.pyc artifacts (never tracked, never deployed)."""
    source_relpath = _deploy_source_relpath(repo_root)
    automation_src = repo_root / source_relpath

    tracked = subprocess.run(
        ["git", "ls-files", "--", str(automation_src)],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        timeout=30,
    )
    assert tracked.returncode == 0, tracked.stderr
    tracked_paths = [line for line in tracked.stdout.splitlines() if line.strip()]
    assert tracked_paths, f"expected at least one git-tracked file under {source_relpath}"

    dest_dir.mkdir(parents=True, exist_ok=True)
    prefix = source_relpath.rstrip("/") + "/"
    for rel_path in tracked_paths:
        rel_to_automation = rel_path[len(prefix):]
        src_file = repo_root / rel_path
        dst_file = dest_dir / rel_to_automation
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_file, dst_file)

    # This migration's files (variables.py in its current, migrated
    # form, and _shared_config_fallback.py) may not be committed yet at
    # the moment this test runs -- `git ls-files` above only sees what's
    # already tracked. Copy them explicitly too, so this test reflects
    # what WILL be deployed once this change is committed, not just
    # what's tracked right now.
    for extra_name in ("variables.py", "_shared_config_fallback.py"):
        src_file = automation_src / extra_name
        dst_file = dest_dir / extra_name
        shutil.copyfile(src_file, dst_file)

    return dest_dir


def _run_isolated(cwd, isolated_automation_dir, import_target: str, extra_sys_path=()):
    """Run a real subprocess with ONLY the isolated deploy-artifact copy
    (plus any explicitly requested extra_sys_path entries, used by the
    collision tests) on sys.path -- cwd is a tmp_path unrelated to the
    repository, so nothing repo-relative leaks in. Isolation itself is
    verified separately by
    test_shared_is_genuinely_unimportable_from_the_isolated_copy_alone.
    Prints the resolved settings module's own __file__ too, so tests can
    assert *which* file was actually loaded, not just the values it
    produced."""
    path_entries = [str(isolated_automation_dir), *[str(p) for p in extra_sys_path]]
    code = textwrap.dedent(
        f"""
        import sys
        for p in {path_entries!r}:
            sys.path.insert(0, p)
        import {import_target} as m
        print('OK', m.project, m.dataset_metadata,
              m.table_mapping['KSA'], m.stage_3, m.tbl_cmpgn_tracker)
        print('SETTINGS_FILE', m.settings.__file__)
        """
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=30,
    )


_EXPECTED_STDOUT = "OK maddictdata Metadata POI_DB_KSA Completion Period Campaign_Tracker"


class TestFallbackMatchesSharedSettings:
    """_shared_config_fallback.py must never drift from
    shared/config/settings.py -- if one changes without the other, this
    fails loudly instead of silently deploying stale or divergent
    values."""

    def test_every_fallback_value_matches_shared_settings(self, repo_root):
        from shared.config import settings
        from tests.conftest import import_module_from_path

        fallback = import_module_from_path(
            "automation_shared_config_fallback_under_test",
            repo_root / "projects" / "automation" / "_shared_config_fallback.py",
        )

        assert fallback.PROJECT_ID == settings.PROJECT_ID
        assert fallback.DATASET_LOCATION_SIGNALS == settings.DATASET_LOCATION_SIGNALS
        assert fallback.DATASET_FOOTFALL == settings.DATASET_FOOTFALL
        assert fallback.DATASET_BACKEND_REPORTS == settings.DATASET_BACKEND_REPORTS
        assert fallback.DATASET_CAMPAIGN_SEGMENTS == settings.DATASET_CAMPAIGN_SEGMENTS
        assert fallback.DATASET_DISTRICT_MAPPING == settings.DATASET_DISTRICT_MAPPING
        assert fallback.DATASET_AUTOMATED_HWG == settings.DATASET_AUTOMATED_HWG
        assert fallback.DATASET_METADATA == settings.DATASET_METADATA
        assert fallback.DATASET_METADATA_PLACELIFT == settings.DATASET_METADATA_PLACELIFT
        assert fallback.TABLE_HOME_GRAPH == settings.TABLE_HOME_GRAPH
        assert fallback.TABLE_CAMPAIGN_TRACKER == settings.TABLE_CAMPAIGN_TRACKER
        assert fallback.TABLE_CAMPAIGN_TEST == settings.TABLE_CAMPAIGN_TEST
        assert fallback.TABLE_BEHAVIOR_LOOKUP == settings.TABLE_BEHAVIOR_LOOKUP
        assert fallback.TABLE_DEVICE_OS_MAPPING == settings.TABLE_DEVICE_OS_MAPPING
        assert dict(fallback.AUTOMATION_COUNTRY_POI_TABLES) == dict(
            settings.AUTOMATION_COUNTRY_POI_TABLES
        )
        assert fallback.STATUS_PRE_VALIDATION == settings.STATUS_PRE_VALIDATION
        assert fallback.STATUS_VALIDATION == settings.STATUS_VALIDATION
        assert fallback.STATUS_ACTIVE == settings.STATUS_ACTIVE
        assert fallback.STATUS_COMPLETION_PERIOD == settings.STATUS_COMPLETION_PERIOD
        assert fallback.STATUS_FINISHED == settings.STATUS_FINISHED
        assert fallback.STATUS_ERROR == settings.STATUS_ERROR
        assert fallback.STATUS_ON_HOLD == settings.STATUS_ON_HOLD
        assert (
            fallback.DRIVE_BACKEND_REPORTS_FOLDER_ID
            == settings.DRIVE_BACKEND_REPORTS_FOLDER_ID
        )
        assert (
            fallback.SECRET_BACKEND_REPORT_TOKEN == settings.SECRET_BACKEND_REPORT_TOKEN
        )
        assert (
            fallback.SECRET_BIGQUERY_CREDENTIALS == settings.SECRET_BIGQUERY_CREDENTIALS
        )
        assert fallback.LEGACY_BIGQUERY_KEY_PATH == settings.LEGACY_BIGQUERY_KEY_PATH
        assert (
            fallback.LEGACY_GOOGLE_SHEETS_KEY_PATH
            == settings.LEGACY_GOOGLE_SHEETS_KEY_PATH
        )


class TestIsolatedDeployArtifact:
    """Reproduces IH-050 exactly: builds a copy of only what the real
    `--source` directory (read from deploy.yml) would actually upload,
    runs a real subprocess with ONLY that copy on sys.path (no repo
    root, so `shared` is genuinely unimportable, matching the real
    deployed Cloud Function), and proves variables.py/main.py still
    import correctly and produce the same values via the fallback path.

    Before the IH-050 fix, `test_variables_importable_...` below would
    fail with `ModuleNotFoundError: No module named 'shared'` -- exactly
    the failure the security review predicted for the real deployed
    artifact.
    """

    @pytest.fixture
    def isolated_automation_dir(self, repo_root, tmp_path):
        dest = tmp_path / "isolated_automation_deploy_copy"
        return _build_isolated_deploy_copy(repo_root, dest)

    def test_shared_is_genuinely_unimportable_from_the_isolated_copy_alone(
        self, tmp_path, isolated_automation_dir
    ):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, sys.argv[1]); import shared",
                str(isolated_automation_dir),
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            timeout=30,
        )
        assert result.returncode != 0
        assert "shared" in result.stderr

    def test_variables_importable_from_the_isolated_deploy_copy(
        self, tmp_path, isolated_automation_dir
    ):
        result = _run_isolated(tmp_path, isolated_automation_dir, "variables")
        assert result.returncode == 0, result.stderr
        assert _EXPECTED_STDOUT in result.stdout

    def test_main_module_importable_from_the_isolated_deploy_copy_without_calling_main(
        self, tmp_path, isolated_automation_dir
    ):
        result = _run_isolated(tmp_path, isolated_automation_dir, "main")
        assert result.returncode == 0, result.stderr
        assert _EXPECTED_STDOUT in result.stdout


class TestCanonicalVsFallbackSelection:
    """Proves *which file* variables.py actually loaded, not just that
    the resulting values happened to match -- a full repository checkout
    must resolve to the real shared/config/settings.py, and an isolated
    deploy copy must resolve to its own bundled fallback file."""

    def test_full_repo_checkout_loads_the_canonical_settings_file(self, repo_root):
        from tests.conftest import import_module_from_path

        mod = import_module_from_path(
            "automation_variables_canonical_selection_check",
            repo_root / "projects" / "automation" / "variables.py",
        )
        expected_canonical = (repo_root / "shared" / "config" / "settings.py").resolve()
        assert os.path.abspath(mod.settings.__file__) == str(expected_canonical)

    def test_isolated_deploy_copy_loads_its_own_bundled_fallback_file(
        self, repo_root, tmp_path
    ):
        isolated_automation_dir = _build_isolated_deploy_copy(
            repo_root, tmp_path / "isolated_for_selection_check"
        )
        result = _run_isolated(tmp_path, isolated_automation_dir, "variables")
        assert result.returncode == 0, result.stderr
        expected_fallback = os.path.abspath(
            str(isolated_automation_dir / "_shared_config_fallback.py")
        )
        settings_file_line = next(
            line for line in result.stdout.splitlines() if line.startswith("SETTINGS_FILE ")
        )
        actual_settings_file = settings_file_line[len("SETTINGS_FILE "):].strip()
        assert os.path.abspath(actual_settings_file) == expected_fallback


class TestConflictingSharedPackageIsIgnored:
    """IH-051 regression test: injects a conflicting, fake
    `shared.config.settings` (with obviously-wrong sentinel values)
    elsewhere on sys.path/sys.modules, in both the full-repo-checkout
    context and the isolated-deploy-artifact context, and proves
    variables.py never picks it up -- because it never performs a
    name-based `import shared...` at all, only exact-path loading."""

    @pytest.fixture
    def fake_shared_package_dir(self, tmp_path):
        """A standalone, importable `shared.config.settings` package
        living entirely outside this repository, with sentinel values
        that would be obviously wrong if ever picked up."""
        fake_root = tmp_path / "fake_shared_root"
        fake_config = fake_root / "shared" / "config"
        fake_config.mkdir(parents=True)
        (fake_root / "shared" / "__init__.py").write_text("", encoding="utf-8")
        (fake_config / "__init__.py").write_text("", encoding="utf-8")
        (fake_config / "settings.py").write_text(
            "PROJECT_ID = 'HIJACKED'\n"
            "DATASET_METADATA = 'HIJACKED'\n"
            "DATASET_LOCATION_SIGNALS = 'HIJACKED'\n"
            "DATASET_FOOTFALL = 'HIJACKED'\n"
            "DATASET_BACKEND_REPORTS = 'HIJACKED'\n"
            "DATASET_CAMPAIGN_SEGMENTS = 'HIJACKED'\n"
            "DATASET_DISTRICT_MAPPING = 'HIJACKED'\n"
            "DATASET_AUTOMATED_HWG = 'HIJACKED'\n"
            "DATASET_METADATA_PLACELIFT = 'HIJACKED'\n"
            "TABLE_HOME_GRAPH = 'HIJACKED'\n"
            "TABLE_CAMPAIGN_TRACKER = 'HIJACKED'\n"
            "TABLE_CAMPAIGN_TEST = 'HIJACKED'\n"
            "TABLE_BEHAVIOR_LOOKUP = 'HIJACKED'\n"
            "TABLE_DEVICE_OS_MAPPING = 'HIJACKED'\n"
            "AUTOMATION_COUNTRY_POI_TABLES = {'XXX': 'HIJACKED'}\n"
            "STATUS_PRE_VALIDATION = 'HIJACKED'\n"
            "STATUS_VALIDATION = 'HIJACKED'\n"
            "STATUS_ACTIVE = 'HIJACKED'\n"
            "STATUS_COMPLETION_PERIOD = 'HIJACKED'\n"
            "STATUS_FINISHED = 'HIJACKED'\n"
            "STATUS_ERROR = 'HIJACKED'\n"
            "STATUS_ON_HOLD = 'HIJACKED'\n"
            "DRIVE_BACKEND_REPORTS_FOLDER_ID = 'HIJACKED'\n"
            "SECRET_BACKEND_REPORT_TOKEN = 'HIJACKED'\n"
            "SECRET_BIGQUERY_CREDENTIALS = 'HIJACKED'\n"
            "LEGACY_BIGQUERY_KEY_PATH = 'HIJACKED'\n"
            "LEGACY_GOOGLE_SHEETS_KEY_PATH = 'HIJACKED'\n",
            encoding="utf-8",
        )
        return fake_root

    def test_full_repo_checkout_ignores_a_conflicting_shared_package(
        self, repo_root, fake_shared_package_dir
    ):
        """Puts the fake package FIRST on sys.path (it would win any
        name-based `import shared...`) and also poisons sys.modules
        directly, then loads variables.py from its real location in a
        full checkout. It must still resolve to the real, canonical
        shared/config/settings.py."""
        import importlib
        import types

        fake_shared_module = types.ModuleType("shared")
        fake_shared_config_module = types.ModuleType("shared.config")
        fake_settings_module = types.ModuleType("shared.config.settings")
        fake_settings_module.PROJECT_ID = "HIJACKED"

        original_sys_path = list(sys.path)
        original_modules = {
            name: sys.modules.get(name)
            for name in ("shared", "shared.config", "shared.config.settings")
        }
        sys.path.insert(0, str(fake_shared_package_dir))
        sys.modules["shared"] = fake_shared_module
        sys.modules["shared.config"] = fake_shared_config_module
        sys.modules["shared.config.settings"] = fake_settings_module
        try:
            from tests.conftest import import_module_from_path

            mod = import_module_from_path(
                "automation_variables_collision_check_in_process",
                repo_root / "projects" / "automation" / "variables.py",
            )
            assert mod.project == "maddictdata"
            assert mod.project != "HIJACKED"
            assert mod.dataset_metadata == "Metadata"
            expected_canonical = (repo_root / "shared" / "config" / "settings.py").resolve()
            assert os.path.abspath(mod.settings.__file__) == str(expected_canonical)
        finally:
            sys.path[:] = original_sys_path
            for name, original in original_modules.items():
                if original is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = original
            importlib.invalidate_caches()

    def test_isolated_deploy_copy_ignores_a_conflicting_shared_package(
        self, repo_root, tmp_path, fake_shared_package_dir
    ):
        """Runs the isolated deploy-artifact copy in a real subprocess
        with the fake shared package ALSO on sys.path (ahead of, and
        alongside, the isolated copy). It must still resolve to its own
        bundled _shared_config_fallback.py, not the fake package -- and
        not fail outright either, since the fix must not depend on
        `shared` being absent, only on never doing a name-based import
        of it."""
        isolated_automation_dir = _build_isolated_deploy_copy(
            repo_root, tmp_path / "isolated_for_collision_check"
        )
        result = _run_isolated(
            tmp_path,
            isolated_automation_dir,
            "variables",
            extra_sys_path=[fake_shared_package_dir],
        )
        assert result.returncode == 0, result.stderr
        assert _EXPECTED_STDOUT in result.stdout
        assert "HIJACKED" not in result.stdout
        expected_fallback = os.path.abspath(
            str(isolated_automation_dir / "_shared_config_fallback.py")
        )
        settings_file_line = next(
            line for line in result.stdout.splitlines() if line.startswith("SETTINGS_FILE ")
        )
        actual_settings_file = settings_file_line[len("SETTINGS_FILE "):].strip()
        assert os.path.abspath(actual_settings_file) == expected_fallback


class TestAmbientCanonicalPathIsNotTrusted:
    """IH-051 round 2 regression test: a flat deployment artifact's
    variables.py computes a "candidate root" two directories above
    itself, purely from its own __file__ -- in a real deployed Cloud
    Function, that candidate root is an AMBIENT HOST PATH with no
    relationship to this repository. This proves that even when a file
    exists at the exact `<candidate_root>/shared/config/settings.py`
    path the flat artifact would compute, it is never trusted unless
    this file's own location also genuinely matches the real
    repository's shape (`<candidate_root>/projects/automation/
    variables.py`) -- which a flat artifact's layout can never satisfy,
    regardless of what happens to exist at the computed path.
    """

    @pytest.fixture
    def flat_artifact_with_ambient_fake_settings(self, repo_root, tmp_path):
        """Builds a flat artifact copy nested exactly two directories
        below a `candidate_root` this test controls, then plants a fake
        `shared/config/settings.py` (with obviously-wrong `"HIJACKED"`
        sentinel values) at the exact path
        `<candidate_root>/shared/config/settings.py` -- precisely what
        variables.py's own two-parents-up computation would land on for
        a flat artifact rooted there."""
        candidate_root = tmp_path / "ambient_host_root"
        flat_dir = candidate_root / "layer" / "flat_deploy_dir"
        _build_isolated_deploy_copy(repo_root, flat_dir)

        fake_config_dir = candidate_root / "shared" / "config"
        fake_config_dir.mkdir(parents=True)
        (candidate_root / "shared" / "__init__.py").write_text("", encoding="utf-8")
        (fake_config_dir / "__init__.py").write_text("", encoding="utf-8")
        (fake_config_dir / "settings.py").write_text(
            "PROJECT_ID = 'HIJACKED'\n"
            "DATASET_METADATA = 'HIJACKED'\n"
            "DATASET_LOCATION_SIGNALS = 'HIJACKED'\n",
            encoding="utf-8",
        )
        return flat_dir

    def test_ambient_fake_settings_at_the_exact_candidate_path_is_ignored(
        self, tmp_path, flat_artifact_with_ambient_fake_settings
    ):
        result = _run_isolated(tmp_path, flat_artifact_with_ambient_fake_settings, "variables")
        assert result.returncode == 0, result.stderr
        assert _EXPECTED_STDOUT in result.stdout
        assert "HIJACKED" not in result.stdout

        expected_fallback = os.path.abspath(
            str(flat_artifact_with_ambient_fake_settings / "_shared_config_fallback.py")
        )
        settings_file_line = next(
            line for line in result.stdout.splitlines() if line.startswith("SETTINGS_FILE ")
        )
        actual_settings_file = settings_file_line[len("SETTINGS_FILE "):].strip()
        assert os.path.abspath(actual_settings_file) == expected_fallback

    def test_main_module_also_ignores_the_ambient_fake_settings(
        self, tmp_path, flat_artifact_with_ambient_fake_settings
    ):
        result = _run_isolated(tmp_path, flat_artifact_with_ambient_fake_settings, "main")
        assert result.returncode == 0, result.stderr
        assert _EXPECTED_STDOUT in result.stdout
        assert "HIJACKED" not in result.stdout


class TestNestedAmbientRootWithoutGitMarkerIsNotTrusted:
    """IH-051 round 3 regression test: round 2's exact-layout +
    samefile checks alone are necessary but NOT sufficient -- they only
    prove this file sits at the relative path
    `projects/automation/variables.py` below some candidate root, not
    that the candidate root is genuinely a checkout of this repository.
    A deployed artifact could itself be placed at
    `<ambient_root>/projects/automation/variables.py` -- matching that
    exact expected shape, satisfying round 2's checks completely --
    while `<ambient_root>` is still not a real checkout. This proves
    that even with the directory shape fully matched, a fake
    `shared/config/settings.py` at the candidate root is still ignored
    when `<ambient_root>/.git` is absent.
    """

    @pytest.fixture
    def nested_ambient_root_without_git(self, repo_root, tmp_path):
        """Copies the deployment artifact to
        `<ambient_root>/projects/automation/` (the exact nested shape a
        real repository checkout would have), deliberately does NOT
        create `<ambient_root>/.git`, and plants a fake
        `shared/config/settings.py` (with `"HIJACKED"` sentinel values)
        at `<ambient_root>/shared/config/settings.py`."""
        ambient_root = tmp_path / "ambient_root_no_git"
        nested_automation_dir = ambient_root / "projects" / "automation"
        _build_isolated_deploy_copy(repo_root, nested_automation_dir)

        assert not (ambient_root / ".git").exists(), (
            "test setup bug: ambient_root must NOT look like a git checkout"
        )

        fake_config_dir = ambient_root / "shared" / "config"
        fake_config_dir.mkdir(parents=True)
        (ambient_root / "shared" / "__init__.py").write_text("", encoding="utf-8")
        (fake_config_dir / "__init__.py").write_text("", encoding="utf-8")
        (fake_config_dir / "settings.py").write_text(
            "PROJECT_ID = 'HIJACKED'\n"
            "DATASET_METADATA = 'HIJACKED'\n"
            "DATASET_LOCATION_SIGNALS = 'HIJACKED'\n",
            encoding="utf-8",
        )
        return nested_automation_dir

    def test_variables_selects_the_bundled_fallback(
        self, tmp_path, nested_ambient_root_without_git
    ):
        result = _run_isolated(tmp_path, nested_ambient_root_without_git, "variables")
        assert result.returncode == 0, result.stderr
        assert _EXPECTED_STDOUT in result.stdout
        assert "HIJACKED" not in result.stdout

        expected_fallback = os.path.abspath(
            str(nested_ambient_root_without_git / "_shared_config_fallback.py")
        )
        settings_file_line = next(
            line for line in result.stdout.splitlines() if line.startswith("SETTINGS_FILE ")
        )
        actual_settings_file = settings_file_line[len("SETTINGS_FILE "):].strip()
        assert os.path.abspath(actual_settings_file) == expected_fallback

    def test_main_module_also_selects_the_bundled_fallback(
        self, tmp_path, nested_ambient_root_without_git
    ):
        result = _run_isolated(tmp_path, nested_ambient_root_without_git, "main")
        assert result.returncode == 0, result.stderr
        assert _EXPECTED_STDOUT in result.stdout
        assert "HIJACKED" not in result.stdout
