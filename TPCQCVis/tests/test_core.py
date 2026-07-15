"""Runnable regression tests for the pipeline's core logic.

These are pure-Python (no ROOT / no GRID) so they run in CI or on any laptop::

    pytest TPCQCVis/tests/test_core.py

They lock in the behaviours that used to live as fragile inline string-slicing
and are easy to break during refactors: run-number parsing, the "which runs to
process" filters, the poll trigger's path parsing, and state persistence.
"""

import os
import tempfile

import pytest

from TPCQCVis.core import paths as P
from TPCQCVis.core.state import StateStore
from TPCQCVis.tools.pollProductions import (
    Production, discover_new, parse_production_paths,
)


# --- paths -------------------------------------------------------------------
@pytest.mark.parametrize("name,expected", [
    ("571438.root", "571438"),
    ("571438_QC.root", "571438"),
    ("571438_1699_QC.root", "571438"),
    ("periodOverview.root", None),
    ("notarun.root", None),
])
def test_run_number_from_file(name, expected):
    assert P.run_number_from_file(name) == expected


def test_is_run_level_file_excludes_timeslices():
    # Reproduces the historical `file[-13] != "_"` filter.
    assert P.is_run_level_file("571438_QC.root") is True
    assert P.is_run_level_file("571438.root") is True
    assert P.is_run_level_file("571438_1699_QC.root") is False


def test_list_runs(tmp_path):
    for n in ["571438.root", "571438_QC.root", "571449.root", "571449_QC.root",
              "periodOverview.root", "571438_1699_QC.root"]:
        (tmp_path / n).write_bytes(b"")
    assert P.list_runs(tmp_path) == ["571438", "571449"]
    assert P.list_runs(tmp_path, processed=True) == ["571438", "571449"]


def test_production_path_roundtrip(tmp_path):
    f = tmp_path / "2026" / "LHC26ai" / "apass1" / "571438_QC.root"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"")
    pp = P.ProductionPath.from_file(f, tmp_path)
    assert (pp.year, pp.period, pp.apass, pp.run) == ("2026", "LHC26ai", "apass1", "571438")
    assert pp.qc_file() == f


# --- poll trigger ------------------------------------------------------------
def test_parse_production_paths():
    paths = [
        "/alice/data/2026/LHC26ai/571438/apass1/2140/QC/001/QC_fullrun.root",
        "/alice/data/2026/LHC26ai/571438/cpass0/2140/QC/001/QC_fullrun.root",
        "   ",
        "/alice/sim/2025/LHC25aj/0/566139/QC/tpcStandardQC.root",  # foreign
    ]
    prods = parse_production_paths(paths)
    assert prods == [
        Production("2026", "LHC26ai", "571438", "apass1", paths[0]),
        Production("2026", "LHC26ai", "571438", "cpass0", paths[1]),
    ]


def test_discover_new_filters_state_and_pass():
    state = StateStore(path=tempfile.mktemp())
    state.mark_processed("LHC26ai", "apass1", "571438", "t0")
    sample = [
        "/alice/data/2026/LHC26ai/571438/apass1/x/QC/001/QC_fullrun.root",
        "/alice/data/2026/LHC26ai/571449/apass1/x/QC/001/QC_fullrun.root",
        "/alice/data/2026/LHC26ai/571449/cpass0/x/QC/001/QC_fullrun.root",
    ]
    new = discover_new("2026", ["LHC26ai"], state, apass="apass1",
                       find_fn=lambda _d: sample)
    assert [(p.period, p.apass, p.run) for p in new] == [("LHC26ai", "apass1", "571449")]


# --- state store -------------------------------------------------------------
def test_state_store_persistence(tmp_path):
    sp = tmp_path / "state.json"
    st = StateStore.load(sp)
    st.mark_processed("LHC26ai", "apass1", "571438", "t0")
    st.set_watermark("alien", "t0")
    st.save()

    st2 = StateStore.load(sp)
    assert st2.is_processed("LHC26ai", "apass1", "571438")
    assert not st2.is_processed("LHC26ai", "apass1", "999999")
    assert st2.watermark("alien") == "t0"


def test_state_store_atomic_save_no_partial(tmp_path):
    sp = tmp_path / "state.json"
    StateStore.load(sp).save()
    # After a save only the final file exists, no leftover temp files.
    leftovers = [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]
    assert leftovers == []
