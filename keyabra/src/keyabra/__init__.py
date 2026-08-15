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

__version__ = "0.2.10"

ENV_DIR = Path.home() / ".config" / "keyabra"


def _vault_lines(path: Path | str) -> tuple[Path, list[str]]:
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"env file not found: {p}")
    mode = p.stat().st_mode & 0o077
    if mode:
        raise PermissionError(
            f"env file {p} is group/other-accessible (chmod 600 it): "
            f"mode {oct(p.stat().st_mode & 0o777)}"
        )
    return p, p.read_text().splitlines()


def _parse_vault_line(p: Path, lineno: int, raw: str) -> tuple[str, str] | None:
    line = raw.strip()
    if not line or line.startswith("#"):
        return None
    if "=" not in line:
        raise ValueError(f"{p}:{lineno}: not NAME=value: {raw!r}")
    name, _, value = line.partition("=")
    name = name.strip()
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1]
    return name, value


def _resolve_vault_entry(p: Path, lineno: int, name: str, value: str) -> str:
    if name.endswith("__FILE"):
        target = Path(value).expanduser()
        if not target.is_file():
            raise FileNotFoundError(f"{p}:{lineno}: {name} -> missing file {target}")
        return target.read_text()
    if name.endswith("__CMD"):
        r = subprocess.run(
            value,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if r.returncode != 0:
            raise RuntimeError(
                f"{p}:{lineno}: {name} command failed with exit {r.returncode}"
            )
        return r.stdout.strip()
    return value


def load_env_file(path: Path | str) -> dict[str, str]:
    """Parse an env-vault file into {NAME: value}, resolving all entries.

    Refuses group/other-readable vaults (chmod 600 it first) — a vault that
    other users can read is not a vault.
    """
    p, lines = _vault_lines(path)
    out: dict[str, str] = {}
    for lineno, raw in enumerate(lines, 1):
        parsed = _parse_vault_line(p, lineno, raw)
        if parsed is None:
            continue
        name, value = parsed
        resolved = _resolve_vault_entry(p, lineno, name, value)
        if name.endswith("__FILE"):
            out[name[: -len("__FILE")]] = resolved
        elif name.endswith("__CMD"):
            out[name[: -len("__CMD")]] = resolved
        else:
            out[name] = resolved
    return out


def load_env_value(path: Path | str, var_name: str) -> str:
    """Resolve one logical vault entry without executing unrelated providers.

    The entire vault still receives permission and syntax validation. Exactly
    one of ``NAME``, ``NAME__FILE``, or ``NAME__CMD`` must define *var_name*;
    ambiguous providers fail closed instead of depending on file order.
    """
    if not var_name or not var_name.strip():
        raise ValueError("secret variable name must not be empty")

    p, lines = _vault_lines(path)
    candidates: list[tuple[int, str, str]] = []
    accepted_names = {var_name, f"{var_name}__FILE", f"{var_name}__CMD"}
    for lineno, raw in enumerate(lines, 1):
        parsed = _parse_vault_line(p, lineno, raw)
        if parsed is None:
            continue
        name, value = parsed
        if name in accepted_names:
            candidates.append((lineno, name, value))

    if not candidates:
        raise KeyError(f"secret variable {var_name!r} is not present")
    if len(candidates) != 1:
        providers = ", ".join(name for _, name, _ in candidates)
        raise ValueError(
            f"secret variable {var_name!r} has multiple providers: {providers}"
        )

    lineno, name, value = candidates[0]
    return _resolve_vault_entry(p, lineno, name, value)


def probe_env_file(path: Path | str, var_name: str) -> dict[str, object]:
    """Validate one logical vault entry without returning its secret value.

    The probe deliberately uses :func:`load_env_value`, so direct values,
    ``__FILE`` pointers, ``__CMD`` providers, vault permissions, and parse
    failures follow the same fail-closed path without executing unrelated
    providers. The returned receipt contains only identity and validation
    metadata.
    """
    if not var_name or not var_name.strip():
        raise ValueError("secret variable name must not be empty")

    vault = Path(path).expanduser()
    resolved = ""
    try:
        resolved = load_env_value(vault, var_name)
        if not resolved:
            raise ValueError(f"secret variable {var_name!r} resolves to an empty value")

        mode = vault.stat().st_mode & 0o777
        return {
            "schema": "keyabra.env-probe/v1",
            "vault": str(vault.resolve()),
            "name": var_name,
            "present": True,
            "non_empty": True,
            "mode": oct(mode),
        }
    finally:
        resolved = ""


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
