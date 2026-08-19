"""
Reproduces IH-001: projects/segments/scripts/query_orchestrator.py accepts
a `codename` parameter in build_query(), but line 162 substitutes the
module-level global `code_name` (bound at import time from
`from input import *`) instead. A caller who explicitly passes a different
`codename` still gets the stale/wrong campaign's code name baked into the
generated SQL.

This is the mechanism behind "requesting campaign 143 can write campaign
167's data" described in docs/code-audit.md.
"""
from __future__ import annotations

from tests.conftest import import_segments_query_orchestrator


def test_codename_parameter_is_silently_ignored_in_favor_of_the_input_py_global(
    monkeypatch,
):
    orch = import_segments_query_orchestrator()

    # Sanity: the module really did pick up a `code_name` global from
    # projects/segments/input.py at import time (whatever value is
    # currently checked in there).
    assert hasattr(orch, "code_name")
    stale_global_value = orch.code_name

    # Simulate main_new.py's attempted fix: inject a DIFFERENT campaign's
    # code_name into the already-imported module's globals, exactly the
    # way shared/utils/compatibility.inject_campaign_variables tries to
    # (and, per IH-001, fails to reach the worker modules in time).
    monkeypatch.setattr(orch, "code_name", "999-DIFFERENT-CAMPAIGN")

    raw_query = "SELECT * FROM t WHERE campaign = '{code_name}'"
    built = orch.build_query(raw_query, country="UAE", codename="143")

    # BUG: IH-001 -- the explicit `codename="143"` argument never appears;
    # whatever `code_name` happens to be bound to in the module globals at
    # call time wins instead. This assertion is the CORRECT diagnosis of
    # the bug's mechanism (module-global wins over the parameter), proven
    # via monkeypatch rather than depending on input.py's current value.
    assert "143" not in built
    assert "999-DIFFERENT-CAMPAIGN" in built


def test_a_direct_grep_style_assertion_on_the_source_line(repo_root):
    """A second, source-level check that the specific substitution at
    fault still reads `code_name` (the global) rather than `codename`
    (the parameter) -- so this test breaks loudly, not silently, the
    moment someone fixes or further changes that line, prompting an
    audit-status update instead of a stale passing test.
    """
    path = repo_root / "projects" / "segments" / "scripts" / "query_orchestrator.py"
    text = path.read_text(encoding="utf-8")
    assert 'query = query.replace("{code_name}", code_name)' in text, (
        "The known-buggy substitution line has changed. If this is an "
        "intentional fix, update docs/code-audit.md IH-001 to Fixed and "
        "adjust/remove this characterization test in the same change."
    )
