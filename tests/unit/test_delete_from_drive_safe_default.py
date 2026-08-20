"""
Regression test for IH-028: projects/segments/scripts/delete_from_drive.py
shipped with DELETE_MODE = True by default, so running it with no
arguments permanently deletes files from a hardcoded Google Drive folder
with no confirmation.

This is a static text/AST check of the source only. It deliberately does
NOT import delete_from_drive.py -- that module is explicitly on the "never
run" list in AGENTS.md/CLAUDE.md, and importing it would still execute its
module-level oauth2client/pydrive2 imports and its own variables.py
loading via importlib, which this test has no need to trigger. No network,
no credentials.
"""
from __future__ import annotations

import ast


def test_delete_mode_defaults_to_false(repo_root):
    path = repo_root / "projects" / "segments" / "scripts" / "delete_from_drive.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "DELETE_MODE" for t in node.targets
        ):
            value = ast.literal_eval(node.value)
            assert value is False, (
                "delete_from_drive.py's DELETE_MODE must default to False "
                "(IH-028) -- a script this destructive must never be armed "
                "by default"
            )
            found = True
            break

    assert found, "expected to find a module-level DELETE_MODE assignment"
