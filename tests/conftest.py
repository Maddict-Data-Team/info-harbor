"""
Shared pytest fixtures for the Info-Harbor offline test suite.

Safety contract (see AGENTS.md / CLAUDE.md):
  - No test in this suite may contact BigQuery, Google Drive, Secret Manager,
    or any other Google Cloud service.
  - No test may read or require real credentials (the local `keys/` directory
    is git-ignored and MUST NOT be opened by any test).
  - Tests exercise the repository's *actual* legacy modules (which use
    `sys.path` hacks and `from module import *`), not reimplementations, so
    a passing suite is evidence about the real code paths.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture(scope="session", autouse=True)
def _repo_root_on_sys_path():
    """Only REPO_ROOT is added globally (needed for `import tests...` and
    `import shared...`). Deliberately does NOT blanket-add every project
    directory: projects/automation, projects/segments, projects/segments/
    scripts, projects/campaign-tracker and projects/poi each ship a file
    named `input.py` and/or `variables.py` with DIFFERENT content. In the
    real app exactly one of those directories is ever on sys.path at a
    time (each entry point only adds its own). Adding all of them here
    would make `from input import *` resolve ambiguously -- a test-harness
    artifact, not the bug under test. import_module_from_path() below adds
    only the one directory a given test actually needs.
    """
    sp = str(REPO_ROOT)
    added = sp not in sys.path
    if added:
        sys.path.insert(0, sp)
    yield
    if added and sp in sys.path:
        sys.path.remove(sp)


@pytest.fixture(autouse=True)
def _block_real_cloud_clients(monkeypatch):
    """Guardrail: fail loudly if any test path tries to build a real,
    network-capable Google client. This does not block the *fake* clients
    in tests/fakes/, only the real google-cloud-* constructors.
    """

    def _forbidden(*_args, **_kwargs):
        raise RuntimeError(
            "A test attempted to construct a real Google Cloud client. "
            "This offline suite must never contact BigQuery/Drive/Secret "
            "Manager. Use tests/fakes instead."
        )

    try:
        import google.oauth2.service_account as sa

        monkeypatch.setattr(
            sa.Credentials, "from_service_account_file", staticmethod(_forbidden)
        )
        monkeypatch.setattr(
            sa.Credentials, "from_service_account_info", staticmethod(_forbidden)
        )
    except ImportError:
        pass

    try:
        import google.cloud.bigquery as bq

        monkeypatch.setattr(bq, "Client", _forbidden)
    except ImportError:
        pass

    try:
        import google.cloud.secretmanager as sm

        monkeypatch.setattr(sm, "SecretManagerServiceClient", _forbidden)
    except ImportError:
        pass

    yield


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def isolated_segments_workspace(tmp_path, monkeypatch):
    """projects/segments scripts use *hardcoded relative paths* such as
    "projects/segments/data/raw" resolved against the current working
    directory (see docs/code-audit.md IH-007/IH-008/IH-009). To exercise
    the real functions without touching the repo's own data/ folders (and
    without needing to modify production code to accept a path parameter,
    which is out of scope for this branch), this fixture builds the same
    relative structure under a temp directory and chdirs into it.
    """
    base = tmp_path / "projects" / "segments" / "data"
    for sub in ("raw", "served", "controlled"):
        (base / sub).mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def import_fresh(module_name: str):
    """Import (or re-import) a legacy flat module so each test starts from
    a clean module namespace, since these modules hold import-time globals
    (e.g. `code_name` from `from input import *`) that tests deliberately
    override.

    NOTE: projects/automation/query_orchestrator.py and
    projects/segments/scripts/query_orchestrator.py are two DIFFERENT files
    that happen to share the same module name (a confirmed duplication --
    see docs/code-audit.md, "Repeated code"). Plain `import module_name`
    is therefore ambiguous whenever both directories are on sys.path.
    Prefer `import_module_from_path` below when the test needs a specific
    one of the two.
    """
    if module_name in sys.modules:
        del sys.modules[module_name]
    return importlib.import_module(module_name)


def import_module_from_path(alias: str, file_path: Path):
    """Load a module from an exact file path under a private alias name,
    so two same-named files (see note above) can be imported
    unambiguously and side by side in one test process. Mirrors the
    importlib.util workaround the repository's own newer scripts already
    use (e.g. projects/segments/scripts/transfer_to_drive.py) to dodge
    this exact collision.

    The loaded module's own directory is temporarily placed at the FRONT
    of sys.path while it executes, so its internal `from variables import
    *` / `from input import *` resolve to the sibling file next to it, not
    to a same-named file elsewhere on sys.path (there are several -- this
    ambiguity is itself IH-001's root cause in production).
    """
    module_dir = str(file_path.parent)
    sys.path.insert(0, module_dir)
    try:
        spec = importlib.util.spec_from_file_location(alias, str(file_path))
        module = importlib.util.module_from_spec(spec)
        sys.modules[alias] = module
        spec.loader.exec_module(module)
    finally:
        if sys.path and sys.path[0] == module_dir:
            sys.path.pop(0)
    return module


AUTOMATION_QUERY_ORCHESTRATOR_PATH = (
    REPO_ROOT / "projects" / "automation" / "query_orchestrator.py"
)
SEGMENTS_QUERY_ORCHESTRATOR_PATH = (
    REPO_ROOT / "projects" / "segments" / "scripts" / "query_orchestrator.py"
)


def import_automation_query_orchestrator():
    return import_module_from_path(
        "automation_query_orchestrator", AUTOMATION_QUERY_ORCHESTRATOR_PATH
    )


def import_segments_query_orchestrator():
    return import_module_from_path(
        "segments_query_orchestrator", SEGMENTS_QUERY_ORCHESTRATOR_PATH
    )
