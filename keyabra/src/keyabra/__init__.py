"""Secure token prompt + command runner."""

from __future__ import annotations

import getpass
import os
import subprocess
import sys
from pathlib import Path

__version__ = "0.1.1"


def prompt_secret(
    label: str = "Token",
    *,
    confirm: bool = False,
    min_len: int = 1,
) -> str:
    """Read a secret from the terminal (hidden input). Never logged or stored."""
    while True:
        value = getpass.getpass(f"{label}: ")
        if len(value) < min_len:
            print("keyabra: too short — try again", file=sys.stderr)
            continue
        if confirm:
            again = getpass.getpass(f"{label} (again): ")
            if value != again:
                print("keyabra: entries did not match — try again", file=sys.stderr)
                continue
        return value


def run_with_env(
    command: list[str],
    env_vars: dict[str, str],
    *,
    cwd: Path | None = None,
) -> int:
    """Run *command* with extra env vars (secrets stay in-process only)."""
    env = os.environ.copy()
    env.update(env_vars)
    try:
        completed = subprocess.run(
            command,
            env=env,
            cwd=str(cwd) if cwd else None,
            check=False,
        )
        return completed.returncode
    finally:
        for key in env_vars:
            env_vars[key] = ""


def find_dist_files(project_dir: Path) -> list[str]:
    dist = project_dir / "dist"
    if not dist.is_dir():
        return []
    files = sorted(dist.glob("*"))
    return [str(p) for p in files if p.is_file() and not p.name.endswith(".asc")]
