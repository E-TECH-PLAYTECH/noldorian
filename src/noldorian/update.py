"""Download a newer Noldorian from PyPI. The vault is not inside the install.

Silent auto-update is not part of the product. ``noldorian doctor`` reports
whether PyPI has a newer version. ``noldorian upgrade --confirm`` downloads it.
``~/.config/noldorian/vault.env`` lives outside the package and is left in place.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any

from noldorian import __version__

PYPI_JSON_URL = "https://pypi.org/pypi/noldorian/json"
PYPI_INDEX = "https://pypi.org/simple"
UPDATE_SCHEMA = "noldorian.update/v1"


def parse_version(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in value.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def install_kind() -> str:
    exe = sys.executable.replace("\\", "/")
    if "/pipx/venvs/noldorian/" in exe:
        return "pipx"
    return "pip"


def upgrade_argv() -> list[str]:
    """Command that downloads noldorian from PyPI. Never a local path."""

    if install_kind() == "pipx" and shutil.which("pipx"):
        return [
            "pipx",
            "upgrade",
            "noldorian",
            f"--pip-args=--index-url {PYPI_INDEX}",
        ]
    return [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "noldorian",
        "--index-url",
        PYPI_INDEX,
    ]


def pypi_status(installed: str | None = None) -> dict[str, Any]:
    """Compare this install to PyPI. Never returns vault values."""

    current = installed or __version__
    command = " ".join(upgrade_argv())
    base: dict[str, Any] = {
        "schema": UPDATE_SCHEMA,
        "installed": current,
        "pypi_latest": None,
        "update_available": False,
        "command": command,
        "index": PYPI_INDEX,
        "vault_persists": True,
        "auto_update": False,
        "error": None,
        "note": (
            "Upgrade replaces the package only. ~/.config/noldorian/vault.env "
            "is not inside the install and is left in place. There is no "
            "background auto-update."
        ),
    }
    req = urllib.request.Request(
        PYPI_JSON_URL,
        headers={"Accept": "application/json", "User-Agent": f"noldorian/{current}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        base["error"] = f"pypi unreachable: {type(exc).__name__}"
        return base
    latest = str((body.get("info") or {}).get("version") or "")
    if not latest:
        base["error"] = "pypi response missing version"
        return base
    base["pypi_latest"] = latest
    base["update_available"] = parse_version(latest) > parse_version(current)
    return base


def run_upgrade(*, confirm: bool = False) -> dict[str, Any]:
    """Download noldorian from PyPI. Does not write the vault."""

    argv = upgrade_argv()
    receipt: dict[str, Any] = {
        "schema": "noldorian.upgrade/v1",
        "command": argv,
        "index": PYPI_INDEX,
        "confirmed": confirm,
        "vault_persists": True,
        "ok": False,
    }
    if any(part.endswith((".whl", ".tar.gz")) or part.startswith("./") for part in argv):
        receipt["error"] = "refusing local-path install; upgrade downloads from PyPI"
        return receipt
    if not confirm:
        receipt["ok"] = True
        receipt["note"] = "pass --confirm to download from PyPI"
        return receipt
    try:
        completed = subprocess.run(argv, check=False)
    except OSError as exc:
        receipt["error"] = str(exc)
        return receipt
    receipt["returncode"] = completed.returncode
    receipt["ok"] = completed.returncode == 0
    return receipt
