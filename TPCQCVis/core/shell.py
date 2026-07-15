"""Uniform subprocess execution with logging and error visibility.

Across the tools, commands were launched with ``subprocess.run(f"python ...",
shell=True)`` and their return codes were ignored, so a failed download would
silently proceed to plotting and reporting.  ``run`` fixes the *observability*
without changing the *control flow*: by default it still returns (does not
raise) so callers that want continue-on-error keep working, but every command
and every failure is now logged, and callers can opt into ``check=True`` to get
an exception on non-zero exit.
"""

from __future__ import annotations

import subprocess
from typing import Sequence, Union

from TPCQCVis.core.logging_setup import get_logger

log = get_logger("tpcqcvis.shell")

Command = Union[str, Sequence[str]]


class CommandError(RuntimeError):
    """Raised by :func:`run` when ``check=True`` and the command fails."""


def run(cmd: Command, *, shell: bool = False, check: bool = False,
        timeout: float | None = None, capture: bool = False,
        label: str | None = None) -> subprocess.CompletedProcess:
    """Run ``cmd``, logging the invocation and any failure.

    Parameters
    ----------
    cmd
        Either an argv list (preferred, ``shell=False``) or a string for
        commands that genuinely need the shell (pipes, globs).
    shell
        Pass through to ``subprocess.run``.  Only use for commands that need
        shell features; prefer argv lists otherwise.
    check
        If True, raise :class:`CommandError` on a non-zero exit.  Defaults to
        False to preserve the historical continue-on-error behaviour.
    capture
        Capture stdout/stderr instead of inheriting the parent's streams.
    label
        Human-readable name used in log messages (defaults to the command).
    """
    printable = cmd if isinstance(cmd, str) else " ".join(map(str, cmd))
    name = label or printable
    log.info("exec: %s", printable)

    proc = subprocess.run(
        cmd, shell=shell, timeout=timeout,
        capture_output=capture, text=True if capture else None,
    )

    if proc.returncode != 0:
        log.error("command failed (exit %s): %s", proc.returncode, name)
        if capture and proc.stderr:
            log.error("stderr: %s", proc.stderr.strip())
        if check:
            raise CommandError(f"{name} exited with {proc.returncode}")
    return proc
