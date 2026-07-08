"""xabra — install, update, and open Everplay-Tech direct-distribution apps.

Noldorian tier: pip-installable, portable, works on any machine with `gh`
authenticated against Everplay-Tech. Every mutating action banks a JSON
receipt under ~/.local/state/xabra/receipts/ — receipts over claims.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

__version__ = "0.1.0"

STATE_DIR = Path(os.environ.get("XABRA_STATE", Path.home() / ".local/state/xabra"))
RECEIPT_DIR = STATE_DIR / "receipts"
BACKUP_DIR = STATE_DIR / "backups"
CONFIG_DIR = Path(os.environ.get("XABRA_CONFIG", Path.home() / ".config/xabra"))
USER_REGISTRY = CONFIG_DIR / "apps.json"

# Built-in registry of Everplay-Tech direct-distribution apps.
# kind: "app"  — a notarized macOS .app delivered in a .dmg → /Applications
#       "cli"  — a binary delivered in a tar.gz → ~/.local/bin
# sources are tried in order:
#   {"type": "release",  "repo": "...", "asset": "<glob>"}   GitHub release asset
#   {"type": "artifact", "repo": "...", "pattern": "<glob>"} newest Actions artifact
#   {"type": "local",    "path": "<glob>"}                   a path on this machine
BUILTIN_APPS: dict[str, dict] = {
    "dud3runner": {
        "kind": "app",
        "app": "DUD3Runner.app",
        "repo": "Everplay-Tech/dud3-p0",
        "sources": [
            {"type": "artifact", "repo": "Everplay-Tech/dud3-p0", "pattern": "DUD3Runner-build-*"},
            {"type": "local", "path": "~/dud3-p0/build/DUD3Runner.dmg"},
        ],
    },
    "tulkas": {
        "kind": "app",
        "app": "TULKAS.app",
        "repo": "Everplay-Tech/TULKAS",
        "sources": [
            {"type": "release", "repo": "Everplay-Tech/TULKAS", "asset": "*.dmg"},
            {"type": "local", "path": "~/TULKAS/build/TULKAS.dmg"},
        ],
    },
    "knot": {
        "kind": "cli",
        "bin": "knot",
        "repo": "Everplay-Tech/knot",
        "sources": [
            {"type": "release", "repo": "Everplay-Tech/knot", "asset": "knot-darwin-arm64.tar.gz"},
        ],
    },
    "fx-lab": {
        "kind": "app",
        "app": "Everplay FX Lab.app",
        "repo": "Everplay-Tech/everplay-fx-lab",
        "sources": [
            {"type": "release", "repo": "Everplay-Tech/everplay-fx-lab", "asset": "*.dmg"},
        ],
    },
}


def load_registry() -> dict[str, dict]:
    """Built-in apps overlaid with ~/.config/xabra/apps.json (same schema)."""
    apps = {k: dict(v) for k, v in BUILTIN_APPS.items()}
    if USER_REGISTRY.is_file():
        try:
            user = json.loads(USER_REGISTRY.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"xabra: bad user registry {USER_REGISTRY}: {exc}")
        for name, spec in user.items():
            if spec is None:
                apps.pop(name, None)
            else:
                apps[name] = spec
    return apps
