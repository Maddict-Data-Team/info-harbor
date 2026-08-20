"""
Regression test for IH-013: projects/segments/queries.ini's query_HG
aliased its source table as `HG` but its join predicate referenced an
unbound alias `ls` (left over from query_POI, a different query above it
in the same file, which does declare an `ls` alias for a different table).
Any campaign using the HG ("Near By Residents") segment type would fail
with a live BigQuery SQL error the moment it ran.

Static text check only -- does not run the query (would require BigQuery).
No network, no credentials.
"""
from __future__ import annotations

import configparser


def _query_hg(repo_root) -> str:
    config = configparser.ConfigParser()
    config.read(repo_root / "projects" / "segments" / "queries.ini")
    return config.get("queries", "query_HG")


def test_query_hg_references_only_its_own_declared_alias(repo_root):
    query_hg = _query_hg(repo_root)

    assert "HG.Longitude" in query_hg
    assert "HG.latitude" in query_hg
    assert "ls." not in query_hg, (
        "query_HG references the unbound alias 'ls' (IH-013) -- it should "
        "only reference 'HG' (its own source table alias) and 'poi' (the "
        "joined table)"
    )
