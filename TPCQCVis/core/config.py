"""Centralised configuration for the TPCQCVis pipeline.

Previously every tool did ``os.environ['TPCQCVIS_DIR']`` at import time, which
crashed with a bare ``KeyError`` when the variable was missing, and hard-coded
deployment details (mailing-list sender, Mattermost webhook, lxplus/eos targets)
directly in the source.  This module gathers all of that in one validated place.

Design goals:

* **Backwards compatible.**  The defaults reproduce the values that were
  previously hard-coded, so behaviour is unchanged when nothing is overridden.
* **Fail clearly.**  A missing required directory raises a readable error that
  says which environment variable to set, instead of a raw ``KeyError``.
* **Override-friendly.**  Every deployment-specific value can be overridden with
  an environment variable, which is what makes the pipeline portable to a new
  maintainer (no more secrets welded into the code).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(RuntimeError):
    """Raised when the environment is not set up correctly."""


def _require_dir(var: str) -> Path:
    value = os.environ.get(var)
    if not value:
        raise ConfigError(
            f"Environment variable {var} is not set. "
            f"Set it in your shell profile (see README 'Setting up')."
        )
    path = Path(value).expanduser()
    if not path.is_dir():
        raise ConfigError(f"{var}={value!r} does not point to an existing directory.")
    return path


def _env(var: str, default: str) -> str:
    """Return an environment override or the historical default."""
    return os.environ.get(var, default)


@dataclass(frozen=True)
class Settings:
    """Resolved, validated configuration for one pipeline run."""

    code_dir: Path
    data_dir: Path
    report_dir: Path

    # --- Daily-report trigger -------------------------------------------------
    # Address that sends the MonALISA "async productions completed" mail.
    daily_report_sender: str = field(default_factory=lambda: _env(
        "TPCQCVIS_REPORT_SENDER", "berkin.ulukutlu@cern.ch"))

    # --- Notifications --------------------------------------------------------
    mattermost_webhook: str = field(default_factory=lambda: _env(
        "TPCQCVIS_MATTERMOST_WEBHOOK",
        "https://mattermost.web.cern.ch/hooks/krtdox9rbtgsxgqif3ijy51y8c"))

    # --- Publishing targets ---------------------------------------------------
    report_web_base: str = field(default_factory=lambda: _env(
        "TPCQCVIS_REPORT_WEB_BASE", "https://alice-tpc-qc.web.cern.ch/reports/"))
    rsync_target: str = field(default_factory=lambda: _env(
        "TPCQCVIS_RSYNC_TARGET",
        "lxplus:/eos/project-a/alice-tpc-qc/www/reports/"))
    update_server_host: str = field(default_factory=lambda: _env(
        "TPCQCVIS_UPDATE_HOST", "lxplus8"))
    update_server_cmd: str = field(default_factory=lambda: _env(
        "TPCQCVIS_UPDATE_CMD",
        "python2 /eos/project-a/alice-tpc-qc/www_resources/updateServer.py"))
    ssh_secret: str = field(default_factory=lambda: _env(
        "TPCQCVIS_SSH_SECRET", "~/.myssh.gpg"))

    @classmethod
    def load(cls) -> "Settings":
        """Read and validate the environment. Raises ConfigError on problems."""
        return cls(
            code_dir=_require_dir("TPCQCVIS_DIR"),
            data_dir=_require_dir("TPCQCVIS_DATA"),
            report_dir=_require_dir("TPCQCVIS_REPORT"),
        )

    # Convenience -------------------------------------------------------------
    @property
    def tools_dir(self) -> Path:
        return self.code_dir / "TPCQCVis" / "tools"

    def tool(self, name: str) -> Path:
        """Absolute path to a tool script, e.g. settings.tool('runPlotter.py')."""
        return self.tools_dir / name


class _LazySettings:
    """Proxy that validates the environment on first access, not on import.

    This lets modules do ``from TPCQCVis.core import settings`` without paying the
    validation cost (or crashing) merely by being imported — important because
    ``--help`` and unit tests should work even without the full environment.
    """

    _cached: Settings | None = None

    def _resolve(self) -> Settings:
        if self._cached is None:
            object.__setattr__(self, "_cached", Settings.load())
        return self._cached  # type: ignore[return-value]

    def __getattr__(self, item):
        return getattr(self._resolve(), item)


settings = _LazySettings()
