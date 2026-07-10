"""Secure token prompt + command runner, with env-vault files.

Env-vault format (0.2.0): a 0600 dotenv-style file the OWNER provisions once.
Plain `NAME=value` lines, `#` comments, and two indirections resolved at run
time so secret material need not be duplicated into the vault:

    NAME__FILE=/absolute/path     -> env NAME = the file's contents
    NAME__CMD=some command        -> env NAME = the command's stdout (stripped)

`keyabra run --env-file PATH -- cmd ...` loads the vault into the child env
(in-process only — never onto argv, never logged). Canonical vault dir:
~/.config/keyabra/ (0700).
"""

from __future__ import annotations

import getpass
import os
import subprocess
import sys
from pathlib import Path

__version__ = "0.2.2"

ENV_DIR = Path.home() / ".config" / "keyabra"


def load_env_file(path: Path | str) -> dict[str, str]:
    """Parse an env-vault file into {NAME: value}, resolving indirections.

    Refuses group/other-readable vaults (chmod 600 it first) — a vault that
    other users can read is not a vault.
    """
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"env file not found: {p}")
    mode = p.stat().st_mode & 0o077
    if mode:
        raise PermissionError(
            f"env file {p} is group/other-accessible (chmod 600 it): "
            f"mode {oct(p.stat().st_mode & 0o777)}"
        )
    out: dict[str, str] = {}
    for lineno, raw in enumerate(p.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{p}:{lineno}: not NAME=value: {raw!r}")
        name, _, value = line.partition("=")
        name = name.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        if name.endswith("__FILE"):
            target = Path(value).expanduser()
            if not target.is_file():
                raise FileNotFoundError(f"{p}:{lineno}: {name} -> missing file {target}")
            out[name[: -len("__FILE")]] = target.read_text()
        elif name.endswith("__CMD"):
            r = subprocess.run(
                value, shell=True, capture_output=True, text=True, timeout=60
            )
            if r.returncode != 0:
                raise RuntimeError(f"{p}:{lineno}: {name} command failed: {r.stderr.strip()[:200]}")
            out[name[: -len("__CMD")]] = r.stdout.strip()
        else:
            out[name] = value
    return out


def prompt_secret(
    label: str = "Token",
    *,
    confirm: bool = False,
    min_len: int = 1,
) -> str:
    """Read a secret from the terminal (hidden input). Never logged or stored.

    Without a TTY (CI, agent-harness shells), getpass either echoes the secret
    or dies in termios/EOFError mid-prompt. Accept one piped line on stdin in
    that case; otherwise refuse with instructions instead of a stack trace.
    """
    if not sys.stdin.isatty():
        value = sys.stdin.readline().rstrip("\n")
        if len(value) >= min_len:
            return value
        print(
            f"keyabra: no TTY and nothing piped on stdin for {label} — "
            "run in a real terminal, pipe the secret in, or use --env-file",
            file=sys.stderr,
        )
        raise SystemExit(2)
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
