"""
Regression test for IH-041: ui/app.py's api_add_campaign() validated the
submitted campaign, then returned {'success': True, ...} despite an
explicit "# TODO: Implement actual database save" immediately above it --
nothing was ever persisted, but the response claimed success.

Static AST/source check only -- does not import or run ui/app.py, staying
on the same "never run" boundary as the other ui/app.py regression tests
in this suite (see test_ui_app_safe_defaults.py). No network, no
credentials.
"""
from __future__ import annotations

import ast


def _function_source(path, func_name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return ast.get_source_segment(source, node)
    raise AssertionError(f"function {func_name!r} not found in {path}")


def test_add_campaign_route_does_not_claim_success_before_persisting(repo_root):
    path = repo_root / "ui" / "app.py"
    func_source = _function_source(path, "api_add_campaign")

    todo_index = func_source.index("Implement actual database save")
    after_todo = func_source[todo_index:]

    assert "'success': False" in after_todo, (
        "api_add_campaign must not claim success (IH-041) while its "
        "persistence step is still a TODO"
    )
    assert "'success': True" not in after_todo, (
        "api_add_campaign still claims success somewhere after the "
        "not-yet-implemented persistence TODO (IH-041)"
    )
