from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY_DIR = Path.home() / ".xadabra"
HISTORY_FILE = HISTORY_DIR / "history.jsonl"


def append_run(script: str, *, source: str) -> None:
    """Record a run locally. Placeholder values are never stored."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "script": script,
    }
    with HISTORY_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
