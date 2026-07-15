"""Single source of truth for parsing the pipeline's path convention.

The pipeline encodes all of its state in a directory layout::

    $TPCQCVIS_DATA/{year}/{period}/{apass}/{run}.root      # raw QC download
    $TPCQCVIS_DATA/{year}/{period}/{apass}/{run}_QC.root   # extracted plots
    $TPCQCVIS_DATA/{year}/{period}/{apass}/{run}.html      # rendered report

Previously each tool re-derived these pieces with ad-hoc string slicing
(``file[-14:-8]``, ``path.split('/')[6]``, ``file[-13] != '_'`` …), with a
different magic index in every file.  Those slices silently break the moment a
path length changes.  This module provides one tested parser so the fragile
arithmetic lives in exactly one place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

# A run number is a >= 6-digit integer. QC files add a "_QC" suffix; time-slice
# files add a "_<timestamp>" segment before the extension.
_RUN_FILE_RE = re.compile(r"^(?P<run>\d{6,})(?P<suffix>_.*)?\.root$")


def run_number_from_file(path: str | Path) -> str | None:
    """Return the run number encoded in a ``.root`` filename, or ``None``.

    Matches ``571438.root`` and ``571438_QC.root`` -> ``"571438"``.
    """
    m = _RUN_FILE_RE.match(Path(path).name)
    return m.group("run") if m else None


def is_qc_file(path: str | Path) -> bool:
    """True for extracted ``{run}_QC.root`` files (not raw, not time-slices)."""
    return Path(path).name.endswith("_QC.root")


def is_run_level_file(path: str | Path) -> bool:
    """True for full-run files, excluding per-time-slice files.

    Reproduces the historical ``file[-13] != '_'`` filter used in
    ``generateReport.py``: a time-slice file looks like ``571438_1699_QC.root``
    and must be skipped, while ``571438_QC.root`` is kept.
    """
    name = Path(path).name
    run = run_number_from_file(name)
    if run is None:
        return False
    # Everything between the run number and ".root":
    middle = name[len(run):-len(".root")]
    return middle in ("", "_QC")


def list_runs(directory: str | Path, *, processed: bool = False) -> List[str]:
    """Return sorted run numbers found in ``directory``.

    ``processed=False`` -> raw ``{run}.root`` inputs (excluding ``_QC`` outputs
    and the ``periodOverview`` aggregate).  ``processed=True`` -> ``{run}_QC``
    outputs.
    """
    directory = Path(directory)
    runs = set()
    for f in directory.glob("*.root"):
        if "periodOverview" in f.name:
            continue
        run = run_number_from_file(f.name)
        if run is None:
            continue
        if processed and is_qc_file(f.name):
            runs.add(run)
        elif not processed and not is_qc_file(f.name) and is_run_level_file(f.name):
            runs.add(run)
    return sorted(runs)


@dataclass(frozen=True)
class ProductionPath:
    """Parsed ``{year}/{period}/{apass}[/{run}]`` production coordinate."""

    data_root: Path
    year: str
    period: str
    apass: str
    run: str | None = None

    @classmethod
    def from_file(cls, path: str | Path, data_root: str | Path) -> "ProductionPath":
        """Parse a QC/report file path relative to ``data_root``."""
        p = Path(path).resolve()
        root = Path(data_root).resolve()
        rel = p.relative_to(root).parts
        if len(rel) < 4:
            raise ValueError(f"{p} is not under a {{year}}/{{period}}/{{apass}} layout")
        year, period, apass = rel[0], rel[1], rel[2]
        return cls(root, year, period, apass, run_number_from_file(p.name))

    @property
    def dir(self) -> Path:
        return self.data_root / self.year / self.period / self.apass

    def raw_file(self, run: str | None = None) -> Path:
        return self.dir / f"{run or self.run}.root"

    def qc_file(self, run: str | None = None) -> Path:
        return self.dir / f"{run or self.run}_QC.root"


def subdirectories(path: str | Path) -> List[str]:
    """Sorted names of immediate subdirectories (used to enumerate periods/passes)."""
    p = Path(path)
    return sorted(d.name for d in p.iterdir() if d.is_dir())
