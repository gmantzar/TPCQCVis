"""Tiny persistent state store for the pipeline.

The pipeline historically kept *no* record of what it had processed — "is this
run done?" was answered by globbing for output files and slicing filenames.
That makes the daily automation non-idempotent and impossible to reason about
when a run is half-processed.

``StateStore`` is a deliberately minimal JSON-backed record of which
``(period, apass, run)`` productions have been handled, plus a per-source
*watermark* (an ISO timestamp) so a polling trigger can ask "what is new since
last time?" without reprocessing everything.  It is intentionally not a
database: a single JSON file is enough at this scale and keeps the deployment
dependency-free and easy to inspect by hand.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable


def _production_key(period: str, apass: str, run: str) -> str:
    return f"{period}/{apass}/{run}"


@dataclass
class StateStore:
    path: Path
    _processed: Dict[str, str] = field(default_factory=dict)   # key -> ISO timestamp
    _watermarks: Dict[str, str] = field(default_factory=dict)  # source -> ISO timestamp

    @classmethod
    def load(cls, path: str | Path) -> "StateStore":
        path = Path(path)
        if path.exists():
            data = json.loads(path.read_text())
            return cls(path, data.get("processed", {}), data.get("watermarks", {}))
        return cls(path)

    def save(self) -> None:
        """Atomically persist the state (temp file + rename) to avoid corruption."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"processed": self._processed, "watermarks": self._watermarks}
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as fh:
                json.dump(payload, fh, indent=2, sort_keys=True)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    # --- production tracking --------------------------------------------------
    def is_processed(self, period: str, apass: str, run: str) -> bool:
        return _production_key(period, apass, run) in self._processed

    def mark_processed(self, period: str, apass: str, run: str, when: str) -> None:
        self._processed[_production_key(period, apass, run)] = when

    def filter_new(self, productions: Iterable[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
        """Return only the ``(period, apass, run)`` tuples not already processed."""
        return [p for p in productions if not self.is_processed(*p)]

    # --- polling watermark ----------------------------------------------------
    def watermark(self, source: str) -> str | None:
        return self._watermarks.get(source)

    def set_watermark(self, source: str, when: str) -> None:
        self._watermarks[source] = when
