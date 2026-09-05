"""xabra — Noldorian operator CLI: vault subcommands + verified-install flags."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

__version__ = "0.2.3"

STATE_DIR = Path(os.environ.get("XABRA_STATE", Path.home() / ".local/state/xabra"))
RECEIPT_DIR = STATE_DIR / "receipts"
BACKUP_DIR = STATE_DIR / "backups"
CONFIG_DIR = Path(os.environ.get("XABRA_CONFIG", Path.home() / ".config/noldorian"))
USER_REGISTRY = CONFIG_DIR / "apps.json"
LEGACY_REGISTRY = Path.home() / ".config" / "xabra" / "apps.json"

# Operator-supplied only. The public package ships no baked application catalog.
BUILTIN_APPS: dict[str, dict] = {}


def load_registry() -> dict[str, dict]:
    """Load ~/.config/noldorian/apps.json, then a 0.2.0 ~/.config/xabra/apps.json overlay."""

    apps: dict[str, dict] = {k: dict(v) for k, v in BUILTIN_APPS.items()}
    for registry in (LEGACY_REGISTRY, USER_REGISTRY):
        if not registry.is_file():
            continue
        try:
            user = json.loads(registry.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"xabra: bad user registry {registry}: {exc}") from exc
        if not isinstance(user, dict):
            raise SystemExit(f"xabra: registry {registry} must be a JSON object")
        for name, spec in user.items():
            if spec is None:
                apps.pop(name, None)
            else:
                apps[name] = spec
    return apps
