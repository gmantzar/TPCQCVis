"""Small logging helper shared by the pipeline tools.

The scripts historically used bare ``print`` statements (some with raw ANSI
colour codes), which makes scheduled/batch runs hard to grep and impossible to
assign a severity.  ``get_logger`` gives every tool a consistent, timestamped
logger while staying a drop-in: the default level and format are intentionally
plain so existing log-scraping keeps working.
"""

from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False


def configure_logging(level: int | str | None = None) -> None:
    """Configure the root logger once. Idempotent.

    Level can be overridden with the ``TPCQCVIS_LOGLEVEL`` environment variable
    (e.g. ``DEBUG``), defaulting to ``INFO``.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    if level is None:
        level = os.environ.get("TPCQCVIS_LOGLEVEL", "INFO")
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    _CONFIGURED = True


def get_logger(name: str = "tpcqcvis") -> logging.Logger:
    """Return a configured logger for ``name``."""
    configure_logging()
    return logging.getLogger(name)
