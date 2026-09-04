"""Owner-provisioned env vault: paste once, run a child, never put secrets on argv.

Vault format: a 0600 dotenv-style file. Plain ``NAME=value`` lines, ``#``
comments, and two indirections resolved at run time:

    NAME__FILE=/absolute/path     -> env NAME = the file's contents
    NAME__CMD=some command        -> env NAME = the command's stdout (stripped)

``xabra run --env-file PATH -- cmd ...`` (also ``noldorian run``) loads the
vault into the child environment in-process only. Canonical vault directory
is ``~/.config/noldorian/``. If that directory has no vault file, a 0.2.0
legacy path under ``~/.config/keyabra/`` is read so existing files still work.
"""

from __future__ import annotations

import getpass
import os
import subprocess
import sys
from pathlib import Path

ENV_DIR = Path.home() / ".config" / "noldorian"
LEGACY_ENV_DIR = Path.home() / ".config" / "keyabra"
DEFAULT_VAULT_NAME = "vault.env"
LEGACY_VAULT_NAME = "keyabra.env"
PROBE_SCHEMA = "noldorian.env-probe/v1"


def default_vault_path() -> Path:
    """Canonical vault if present; otherwise the 0.2.0 legacy file; else canonical."""

    canonical = ENV_DIR / DEFAULT_VAULT_NAME
    if canonical.is_file():
        return canonical
    legacy = LEGACY_ENV_DIR / LEGACY_VAULT_NAME
    if legacy.is_file():
        return legacy
    return canonical


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


def _logical_name(name: str) -> str:
    if name.endswith("__FILE"):
        return name[: -len("__FILE")]
    if name.endswith("__CMD"):
        return name[: -len("__CMD")]
    return name


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

    Refuses group/other-readable vaults (chmod 600 it first).
    """
    p, lines = _vault_lines(path)
    out: dict[str, str] = {}
    for lineno, raw in enumerate(lines, 1):
        parsed = _parse_vault_line(p, lineno, raw)
        if parsed is None:
            continue
        name, value = parsed
        resolved = _resolve_vault_entry(p, lineno, name, value)
        out[_logical_name(name)] = resolved
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


def list_vault_names(path: Path | str) -> list[str]:
    """Return logical variable names only. Never returns values."""

    p, lines = _vault_lines(path)
    names: list[str] = []
    seen: set[str] = set()
    for lineno, raw in enumerate(lines, 1):
        parsed = _parse_vault_line(p, lineno, raw)
        if parsed is None:
            continue
        logical = _logical_name(parsed[0])
        if logical not in seen:
            seen.add(logical)
            names.append(logical)
    return names


def probe_env_file(path: Path | str, var_name: str) -> dict[str, object]:
    """Validate one logical vault entry without returning its secret value."""

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
            "schema": PROBE_SCHEMA,
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
    """Read a secret from the terminal (hidden input). Never logged or stored."""

    if not sys.stdin.isatty():
        value = sys.stdin.readline().rstrip("\n")
        if len(value) >= min_len:
            return value
        print(
            f"noldorian: no TTY and nothing piped on stdin for {label} — "
            "run in a real terminal, pipe the secret in, or use --env-file",
            file=sys.stderr,
        )
        raise SystemExit(2)
    while True:
        value = getpass.getpass(f"{label}: ")
        if len(value) < min_len:
            print("noldorian: too short — try again", file=sys.stderr)
            continue
        if confirm:
            again = getpass.getpass(f"{label} (again): ")
            if value != again:
                print("noldorian: entries did not match — try again", file=sys.stderr)
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


def child_run_template(command: str = "<command>") -> dict[str, str]:
    """Describe how an owner runs a child with the vault. Never includes values."""

    vault = default_vault_path()
    return {
        "schema": "noldorian.child-run-template/v1",
        "command": f"xabra run --env-file {vault} -- {command}",
        "equivalent": f"noldorian run --env-file {vault} -- {command}",
        "note": (
            "The owner runs this locally. Secrets stay in the child environment; "
            "they are not returned to agents, chat, argv, or MCP."
        ),
    }
