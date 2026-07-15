"""Poll-based trigger for the daily async-QC pipeline.

This is the recommended replacement for ``dailyAsyncFromEmail.py``.  Instead of
scraping the MonALISA notification e-mail from one person's Gmail account (which
tied the whole automation to that individual's credentials and broke when they
left), this tool reacts to the *artifacts themselves*: it asks AliEn which
``QC_fullrun.root`` files exist for the periods we care about, remembers which
ones it has already handled in a small state file, and processes only the new
ones.

Advantages over the e-mail trigger:

* No personal identity / OAuth token to expire — it uses the same GRID
  certificate the rest of the pipeline already needs.
* No brittle prose parsing — the source of truth is the file listing.
* Idempotent and resumable — the :class:`StateStore` watermark means a missed
  or crashed run simply gets picked up next time.

The AliEn call is injected (``find_fn``) so the discovery/decision logic is
unit-testable without GRID access; see ``tests`` for the pure-function checks.

Usage::

    python pollProductions.py --year 2026 --periods LHC26ai LHC26ae --apass apass1 --process
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

from TPCQCVis.core import settings, get_logger
from TPCQCVis.core.shell import run as shrun
from TPCQCVis.core.state import StateStore

log = get_logger("tpcqcvis.poll")

# AliEn data layout: /alice/data/{year}/{period}/{run}/{apass}/.../QC_fullrun.root
_QC_PATH_RE = re.compile(
    r"/alice/data/(?P<year>\d{4})/(?P<period>LHC\w+?)/(?P<run>\d{6,})/(?P<apass>[^/]+)/"
)


@dataclass(frozen=True)
class Production:
    year: str
    period: str
    run: str
    apass: str
    alien_path: str


def parse_production_paths(paths: Sequence[str]) -> List[Production]:
    """Parse AliEn ``QC_fullrun.root`` paths into structured productions.

    Pure function: unknown/foreign paths are skipped.  This is the core of the
    trigger and is fully unit-testable without GRID access.
    """
    out: List[Production] = []
    for path in paths:
        path = path.strip()
        if not path:
            continue
        m = _QC_PATH_RE.search(path)
        if not m:
            log.debug("Skipping unrecognised path: %s", path)
            continue
        out.append(Production(m["year"], m["period"], m["run"], m["apass"], path))
    return out


def alien_find_qc(remote_dir: str) -> List[str]:
    """Return AliEn paths of ``QC_fullrun.root`` files under ``remote_dir``.

    This is the only part that talks to the GRID; it is injected into
    :func:`discover_new` so the rest of the logic can be tested offline.
    """
    result = subprocess.run(["alien.py", "find", remote_dir, "QC_fullrun.root"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        log.error("alien.py find failed for %s: %s", remote_dir, result.stderr.strip())
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def discover_new(year: str, periods: Sequence[str], state: StateStore, *,
                 apass: Optional[str] = None,
                 find_fn: Callable[[str], List[str]] = alien_find_qc) -> List[Production]:
    """Discover productions on the GRID that have not yet been processed."""
    discovered: List[Production] = []
    for period in periods:
        remote_dir = f"/alice/data/{year}/{period}/"
        log.info("Polling %s", remote_dir)
        productions = parse_production_paths(find_fn(remote_dir))
        if apass:
            productions = [p for p in productions if p.apass == apass]
        discovered.extend(productions)

    new = [p for p in discovered
           if not state.is_processed(p.period, p.apass, p.run)]
    log.info("Discovered %d productions, %d are new", len(discovered), len(new))
    return new


def process(new: Sequence[Production], year: str, state: StateStore,
            threads: int = 1) -> None:
    """Run the existing download/plot/report chain for each new period/pass.

    Reuses ``qc_master.py`` (the same entry point the e-mail trigger used) so the
    processing behaviour is unchanged — only the *triggering* is different.
    """
    now = datetime.datetime.now().isoformat(timespec="seconds")
    # Group by (period, apass): qc_master processes a whole pass at once.
    period_passes = sorted({(p.period, p.apass) for p in new})
    for period, apass in period_passes:
        log.info("Processing %s/%s (%s)", period, apass, year)
        shrun([sys.executable, str(settings.tool("qc_master.py")),
               "-t", str(threads), "--path", f"{settings.data_dir}/{year}",
               "--apass", apass, "--download", "--plot", "--report", period])
        # Mark every run of this period/pass as processed.
        for p in new:
            if p.period == period and p.apass == apass:
                state.mark_processed(p.period, p.apass, p.run, now)
    state.save()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--year", required=True, help="Data-taking year, e.g. 2026")
    parser.add_argument("--periods", nargs="+", required=True,
                        help="Periods to poll, e.g. LHC26ai LHC26ae")
    parser.add_argument("--apass", help="Restrict to a single pass (e.g. apass1)")
    parser.add_argument("-t", "--num_threads", type=int, default=1)
    parser.add_argument("--state", default=None,
                        help="State file (default: <report_dir>/poll_state.json)")
    parser.add_argument("--process", action="store_true",
                        help="Actually download/plot/report the new productions "
                             "(otherwise just list them)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    state_path = args.state or (settings.report_dir / "poll_state.json")
    state = StateStore.load(state_path)

    new = discover_new(args.year, args.periods, state, apass=args.apass)
    for p in new:
        print(f"NEW  {p.period}/{p.apass}/{p.run}")

    if args.process and new:
        process(new, args.year, state, threads=args.num_threads)
    elif not new:
        log.info("Nothing new to process.")


if __name__ == "__main__":
    main()
