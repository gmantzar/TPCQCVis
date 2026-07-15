"""Orchestrate download / plot / report for one or more periods.

This is the manual entry point (the scheduled one is ``dailyAsyncFromEmail``).
For every requested period (and pass) it fans out to the stage scripts.

Refactor notes (behaviour preserved):

* The stage functions no longer read the global ``args`` object — the flags and
  parameters they need are passed in explicitly, so the control flow is
  testable and there are no hidden globals.
* Sub-commands are launched through :func:`TPCQCVis.core.shell.run` as argv
  lists (no ``shell=True``); the command *content* is identical to before, but
  failures are now logged instead of silently ignored.
* Environment variables come from the validated :data:`settings` object.
"""

import argparse
import concurrent.futures
import sys

from TPCQCVis.core import settings, get_logger
from TPCQCVis.core import paths as P
from TPCQCVis.core.shell import run

log = get_logger("tpcqcvis.qc_master")

PY = sys.executable  # the interpreter running us (the alienv python), reused for children


def download(path, period, apass):
    remote = f"/alice/data/20{period[3:5]}/{period}/"
    log.info("Download: %s/%s/%s/", path, period, apass)
    run([PY, str(settings.tool("downloadFromAlien.py")),
         f"{path}/{period}/{apass}/", remote, apass])


def plot(path, period, apass, rerun):
    stage_dir = f"{path}/{period}/{apass}/"
    if not P.Path(stage_dir).is_dir():
        return
    cmd = [PY, str(settings.tool("runPlotter.py")), stage_dir]
    if rerun:
        cmd.append("--rerun")
    log.info("Plot: %s", stage_dir)
    run(cmd)


def generate_report(path, period, apass, num_threads):
    stage_dir = f"{path}/{period}/{apass}/"
    if not P.Path(stage_dir).is_dir():
        return
    log.info("Report: %s", stage_dir)
    run([PY, str(settings.tool("generateReport.py")),
         path, period, apass, "-t", str(num_threads)])


def _passes_for(path, period, apass):
    """Explicit apass if given, else every pass sub-directory of the period."""
    if apass:
        return [apass]
    passes = P.subdirectories(f"{path}/{period}")
    if not passes:
        raise RuntimeError(f"No apass folders found under {path}/{period}/")
    return passes


def execute_commands(path, period_list, apass, num_threads, rerun,
                     do_download, do_plot, do_report):
    # Default to every period folder under `path` when none are listed.
    if not period_list:
        period_list = P.subdirectories(path)
        if not period_list:
            raise RuntimeError(f"No period folders found under {path}/")
        log.info("No period list provided. Running for %s", period_list)

    if do_download:
        # Downloads stay sequential (single worker) due to LRZ rate limits.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            futures = [executor.submit(download, path, period, apass)
                       for period in period_list]
            concurrent.futures.wait(futures)

    if do_plot:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for period in period_list:
                for ap in _passes_for(path, period, apass):
                    futures.append(executor.submit(plot, path, period, ap, rerun))
            concurrent.futures.wait(futures)

    if do_report:
        if not path:
            log.error("Missing path argument for report command")
            return
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            # Split the thread budget across periods so children don't oversubscribe.
            parallel_threads = max(1, num_threads // len(period_list))
            futures = []
            for period in period_list:
                for ap in _passes_for(path, period, apass):
                    futures.append(executor.submit(
                        generate_report, path, period, ap, parallel_threads))
            concurrent.futures.wait(futures)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Execute pipeline stages for each period")
    parser.add_argument("period_list", nargs="*", help="List of period strings")
    parser.add_argument("-d", "--download", action="store_true", help="Run download command")
    parser.add_argument("-p", "--plot", action="store_true", help="Run plotter command")
    parser.add_argument("-r", "--report", action="store_true", help="Run report command")
    parser.add_argument("-rr", "--rerun", action="store_true",
                        help="Rerun plotter for existing periods")
    parser.add_argument("--path", help="Path string for generateReport command")
    parser.add_argument("--apass", help="Apass string for generateReport command")
    parser.add_argument("-t", "--num_threads", type=int, default=1,
                        help="Number of threads to be used (default: 1)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    log.info("Path: %s", args.path)
    execute_commands(
        path=args.path, period_list=args.period_list, apass=args.apass,
        num_threads=args.num_threads, rerun=args.rerun,
        do_download=args.download, do_plot=args.plot, do_report=args.report,
    )


if __name__ == "__main__":
    main()
