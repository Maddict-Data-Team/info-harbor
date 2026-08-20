"""
Regression test protecting IH-026's fix: ui/app.py must not run with
debug=True or bind to 0.0.0.0.

This reads and parses ui/app.py's source with `ast` rather than importing
the module, so it never executes Flask app setup, builds a real client, or
opens a socket -- no network, no credentials. Matches the audit's own
verification method for IH-026 ("Static reading... not run").
"""
from __future__ import annotations

import ast


def _find_app_run_call(tree: ast.Module) -> ast.Call:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "app"
        ):
            return node
    raise AssertionError("no app.run(...) call found in ui/app.py")


def _kwarg_value(call: ast.Call, name: str):
    for kw in call.keywords:
        if kw.arg == name:
            return ast.literal_eval(kw.value)
    raise AssertionError(f"app.run(...) has no keyword argument {name!r}")


class TestUiAppSafeRunDefaults:
    """# FIXED: IH-026 -- app.run() must never default to debug=True or
    host='0.0.0.0', which exposes the Werkzeug interactive debugger (RCE)
    to the network. Guards against a silent regression back to the
    original defaults.
    """

    def test_app_run_uses_debug_false_and_localhost(self, repo_root):
        source = (repo_root / "ui" / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(source, filename="ui/app.py")
        call = _find_app_run_call(tree)

        assert _kwarg_value(call, "debug") is False, (
            "ui/app.py's app.run() must not default to debug=True (IH-026)"
        )
        assert _kwarg_value(call, "host") == "127.0.0.1", (
            "ui/app.py's app.run() must not default to host='0.0.0.0' (IH-026)"
        )
