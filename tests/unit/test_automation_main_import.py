"""
Import tests for IH-045 and IH-047:

- IH-045: projects/automation/main.py did flat, unqualified imports
  (`import upload_backend`, `import query_orchestrator`, `from variables
  import *`) with no sys.path handling for its own directory, so
  `import projects.automation.main` (e.g. ui/app.py's /automation route)
  failed with ModuleNotFoundError -- the same class of bug as IH-015 for
  projects/segments/main_new.py.

- IH-047 (found by automated review of the IH-045 fix): fixing the
  ModuleNotFoundError with a plain `sys.path.append` alone left the flat
  imports order-dependent. projects/segments/scripts/query_orchestrator.py
  is a DIFFERENT file that shares the exact name "query_orchestrator",
  and projects/segments/scripts/get_segments_raw.py does a flat `import
  query_orchestrator` of its own -- in one long-running process (like
  ui/app.py, which can reach both /campaign/<code>/run/segments and
  /automation), whichever loads first "wins" the plain
  sys.modules['query_orchestrator']/['variables'] entries, and the
  second file to load silently binds to the WRONG same-named module
  instead of raising an error. projects/automation/main.py,
  query_orchestrator.py, and upload_backend.py were all changed to load
  their local dependencies (each other, and variables.py) via
  importlib.util.spec_from_file_location under private aliases instead
  of plain imports, so they can never be affected by this collision
  regardless of import order.

None of these tests call main() (constructs real Secret Manager/
BigQuery/Drive clients) or any campaign-processing function. No network,
no credentials.

Every test here that imports projects.segments.main_new (to reproduce the
IH-047 collision scenario) restores any sys.modules entries it disturbed
for 'variables'/'query_orchestrator' afterward, so it can't leak a stale
cache entry into an unrelated later test.
"""
from __future__ import annotations

import sys

_POLLUTABLE_MODULE_NAMES = ("variables", "query_orchestrator", "upload_backend")


class _RestoreSysModules:
    def __enter__(self):
        self._pre_existing = {name: sys.modules.get(name) for name in _POLLUTABLE_MODULE_NAMES}
        return self

    def __exit__(self, *exc_info):
        for name, original in self._pre_existing.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def test_automation_main_imports_successfully_and_exposes_a_callable_main(monkeypatch, repo_root):
    monkeypatch.syspath_prepend(str(repo_root))

    with _RestoreSysModules():
        import projects.automation.main as automation_main

        assert callable(automation_main.main)
        assert automation_main.main.__name__ == "main"


def test_automation_main_resolves_its_own_query_orchestrator_and_upload_backend(
    monkeypatch, repo_root
):
    """Stronger than the smoke test above: confirms the loaded
    submodules actually come from projects/automation/, not just that
    *some* module ended up bound to those names."""
    monkeypatch.syspath_prepend(str(repo_root))

    with _RestoreSysModules():
        import projects.automation.main as automation_main

        automation_dir = str(repo_root / "projects" / "automation")
        assert automation_main.query_orchestrator.__file__.startswith(automation_dir)
        assert automation_main.upload_backend.__file__.startswith(automation_dir)
        assert hasattr(automation_main.query_orchestrator, "run_by_codename")
        # stage_3 is automation-specific (projects/automation/variables.py);
        # projects/segments/scripts/variables.py does not define it.
        assert hasattr(automation_main, "stage_3")


def test_automation_main_is_import_order_safe_against_the_segments_collision(
    monkeypatch, repo_root
):
    """# FIXED: IH-047 -- directly reproduces the scenario the reviewer
    described: import a projects/segments/scripts/ worker module FIRST
    (populating sys.modules['query_orchestrator'] and ['variables'] with
    SEGMENTS' files, via that project's own flat imports), then import
    projects.automation.main, and confirm it still resolves to its own
    files rather than silently reusing segments' cached modules."""
    monkeypatch.syspath_prepend(str(repo_root))

    with _RestoreSysModules():
        import projects.segments.main_new  # noqa: F401 -- triggers segments' flat imports

        assert "query_orchestrator" in sys.modules, (
            "test assumption broken: projects.segments.main_new's import chain "
            "no longer populates sys.modules['query_orchestrator'] -- if "
            "segments' own imports changed, this collision scenario may no "
            "longer be reproducible this way and this test should be revisited"
        )

        import projects.automation.main as automation_main

        automation_dir = str(repo_root / "projects" / "automation")
        assert automation_main.query_orchestrator.__file__.startswith(automation_dir), (
            "projects.automation.main.query_orchestrator resolved to the wrong "
            "file after projects.segments.main_new was imported first (IH-047)"
        )
        assert hasattr(automation_main, "stage_3"), (
            "projects.automation.main is missing stage_3 -- its `from variables "
            "import *` equivalent silently picked up segments' variables.py "
            "instead of its own (IH-047)"
        )
