"""
IH-050 (found by security review of Phase 2e / IH-048's Automation
migration, before that change was committed): `.github/workflows/deploy.yml:31`
deploys the Cloud Function via `gcloud functions deploy ... --source
projects/automation`, which uploads ONLY that directory. Phase 2e made
`projects/automation/variables.py` import `shared.config.settings`, which
lives outside `projects/automation/` -- that import would fail in the
deployed artifact, which never contains `shared/` at all. Offline tests
that import from a full repository checkout (as every other test in this
suite does) cannot detect this: the repo root is on `sys.path`, so
`shared` is always importable there regardless of what the real deploy
artifact would contain.

Fixed by making `projects/automation/variables.py` prefer
`shared.config.settings` (the parity-checked canonical source, reachable
in any full-repository context) and fall back to
`projects/automation/_shared_config_fallback.py` -- a byte-identical,
self-contained copy that IS part of the deployed source tree -- only when
`shared` is not importable.

This file proves two separate things, neither of which any other test in
this suite can:

1. `_shared_config_fallback.py`'s values never drift from
   `shared/config/settings.py`'s (`TestFallbackMatchesSharedSettings`).
2. An isolated copy of exactly what `--source projects/automation` would
   upload -- built from the real files on disk, excluding only
   `__pycache__` and files not tracked by git (which a real CI checkout,
   and therefore a real deploy, would never contain either) -- still
   imports `variables.py` and `main.py` correctly, through the fallback
   path, with `shared` genuinely unimportable (`TestIsolatedDeployArtifact`).

No test here constructs a real Google client or touches network/
credentials: variables.py only imports `bigquery` for `SchemaField`
objects (plain data classes), never a client; main.py's `main()`/
`query_bigquery_and_process()` are never called.
"""
from __future__ import annotations

import shutil
import subprocess
import sys

import pytest


AUTOMATION_DIR_NAME = "automation"


def _build_isolated_deploy_copy(repo_root, dest_dir):
    """Copy exactly what a real `gcloud functions deploy --source
    projects/automation` would upload from this working tree: every file
    under projects/automation/ that is tracked by git (a real deploy runs
    from a `git checkout`, not this machine's local working tree, so an
    untracked file here -- e.g. a stray local test fixture -- would never
    reach a real deploy either), minus __pycache__/.pyc artifacts (never
    tracked, never deployed)."""
    automation_src = repo_root / "projects" / AUTOMATION_DIR_NAME

    tracked = subprocess.run(
        ["git", "ls-files", "--", str(automation_src)],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        timeout=30,
    )
    assert tracked.returncode == 0, tracked.stderr
    tracked_paths = [line for line in tracked.stdout.splitlines() if line.strip()]
    assert tracked_paths, "expected at least one git-tracked file under projects/automation"

    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel_path in tracked_paths:
        rel_to_automation = rel_path[len("projects/automation/") :]
        src_file = repo_root / rel_path
        dst_file = dest_dir / rel_to_automation
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_file, dst_file)

    # This migration's two new files are not yet committed (this branch
    # hasn't been committed at all, per the explicit instruction to wait
    # for review) -- `git ls-files` above only sees what's already
    # tracked. Copy them explicitly too, so this test reflects what WILL
    # be deployed once this change is committed, not just what's tracked
    # right now.
    for extra_name in ("variables.py", "_shared_config_fallback.py"):
        src_file = automation_src / extra_name
        dst_file = dest_dir / extra_name
        shutil.copyfile(src_file, dst_file)

    return dest_dir


def _run_isolated(cwd, isolated_automation_dir, import_target: str):
    """Run a real subprocess with ONLY the isolated deploy-artifact copy
    on sys.path (cwd is a tmp_path unrelated to the repository, so
    nothing repo-relative leaks in). Isolation itself is verified
    separately by test_shared_is_genuinely_unimportable_from_the_isolated_copy_alone."""
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        f"import {import_target} as m; "
        "print('OK', m.project, m.dataset_metadata, "
        "m.table_mapping['KSA'], m.stage_3, m.tbl_cmpgn_tracker)"
    )
    return subprocess.run(
        [sys.executable, "-c", code, str(isolated_automation_dir)],
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
    """Reproduces IH-050 exactly: builds a copy of only what
    `--source projects/automation` would actually upload, runs a real
    subprocess with ONLY that copy on sys.path (no repo root, so `shared`
    is genuinely unimportable, matching the real deployed Cloud
    Function), and proves variables.py/main.py still import correctly
    and produce the same values via the fallback path.

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
            [sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import shared", str(isolated_automation_dir)],
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
