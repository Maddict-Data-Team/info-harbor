"""
Smoke-import test for IH-015: projects/segments/main_new.py imported its
worker scripts via dotted paths (`from
projects.segments.scripts.get_segments_raw import get_raw_segments`, etc.),
but those worker scripts do their own flat, unqualified imports internally
(`from variables import *`, `import query_orchestrator`), which require
projects/segments/scripts to be on sys.path -- something main_new.py never
did (unlike projects/segments/main.py, which does). Importing main_new.py
failed with ModuleNotFoundError before the fix.

This only imports the module and confirms `main` is callable; it does not
call main() itself (would authenticate to real BigQuery/Drive via
authenticate_get_clients()). No network, no credentials.
"""
from __future__ import annotations


def test_main_new_imports_successfully_and_exposes_a_callable_main(repo_root, monkeypatch):
    monkeypatch.syspath_prepend(str(repo_root))

    import projects.segments.main_new as segments_main_new

    assert callable(segments_main_new.main)
    assert segments_main_new.main.__name__ == "main"
