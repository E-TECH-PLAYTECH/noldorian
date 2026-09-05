"""Install / vault / optional-extension doctor. Works with no broker socket."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from noldorian import __version__
from noldorian.client import DEFAULT_SOCKET_PATH
from noldorian import vault as vault_mod
from noldorian.update import pypi_status


def _which_cli(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for candidate in (
        Path.home() / "Library/Python/3.9/bin" / name,
        Path.home() / "Library/Python/3.10/bin" / name,
        Path.home() / "Library/Python/3.11/bin" / name,
        Path.home() / "Library/Python/3.12/bin" / name,
        Path.home() / ".local/bin" / name,
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _vault_section() -> dict[str, object]:
    canonical = Path(vault_mod.ENV_DIR) / "vault.env"
    leftover = vault_mod.leftover_vault_path()
    leftover_present = leftover.is_file()
    if leftover_present and not canonical.is_file():
        return {
            "canonical_dir": str(Path(vault_mod.ENV_DIR)),
            "canonical_vault": str(canonical),
            "legacy_dir": str(Path(vault_mod.LEGACY_ENV_DIR)),
            "legacy_vault": str(leftover),
            "leftover_present": True,
            "active_vault": None,
            "present": False,
            "mode": None,
            "names": [],
            "error": (
                "leftover vault file still present; noldorian will not create "
                "an empty canonical vault.env on top of it. Backup and remove "
                f"{leftover}, then rerun noldorian doctor so noldorian can "
                "create ~/.config/noldorian itself."
            ),
        }
    vault_mod.ensure_canonical_home()
    active = vault_mod.default_vault_path()
    present = active.is_file()
    names: list[str] = []
    mode: str | None = None
    error: str | None = None
    if present:
        try:
            mode = oct(active.stat().st_mode & 0o777)
            names = vault_mod.list_vault_names(active)
        except (OSError, ValueError, PermissionError) as exc:
            error = str(exc)
    return {
        "canonical_dir": str(Path(vault_mod.ENV_DIR)),
        "canonical_vault": str(canonical),
        "legacy_dir": str(Path(vault_mod.LEGACY_ENV_DIR)),
        "legacy_vault": str(leftover),
        "leftover_present": leftover_present,
        "active_vault": str(active) if present else None,
        "present": present,
        "mode": mode,
        "names": names,
        "error": error,
    }


def _extension_section(socket_path: Path | None = None) -> dict[str, object]:
    path = Path(socket_path) if socket_path is not None else DEFAULT_SOCKET_PATH
    present = path.exists()
    return {
        "socket": str(path),
        "present": present,
        "status": "ready" if present else "absent",
        "note": (
            "Optional Gondolin extension. Everyday vault use does not require it."
            if not present
            else "Unix socket is present; public client may query it."
        ),
    }


def doctor_report(*, socket_path: Path | None = None) -> dict[str, object]:
    """Non-secret status of this Noldorian install."""

    vault = _vault_section()
    extension = _extension_section(socket_path)
    clis = {
        name: _which_cli(name)
        for name in ("noldorian", "noldorian-mcp", "xabra", "xadabra", "xalakazam", "abra")
    }
    vault_ok = vault.get("error") is None
    return {
        "schema": "noldorian.doctor/v1",
        "version": __version__,
        "ok": vault_ok,
        "install": "python3 -m pip install noldorian",
        "python": sys.executable,
        "clis": clis,
        "vault": vault,
        "extension": extension,
        "update": pypi_status(__version__),
    }
