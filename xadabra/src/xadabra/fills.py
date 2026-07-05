from __future__ import annotations

import os
import sys
from pathlib import Path

from xadabra.parser import Placeholder, normalize_path_input
from xadabra.prompts import prompt_for_placeholder


def env_var_name(name: str) -> str:
    return f"XADABRA_{name}"


def parse_set_args(pairs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise ValueError(f"invalid --set (need NAME=value): {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"invalid --set (empty name): {item}")
        out[key] = value
    return out


def _validate_path(value: str) -> str:
    value = normalize_path_input(value)
    path = Path(os.path.expanduser(value))
    if not path.exists():
        raise ValueError(f"path not found: {value}")
    return str(path)


def prefill_placeholder(ph: Placeholder, overrides: dict[str, str]) -> str | None:
    """Return a value without prompting, or None if the operator must be asked."""
    if ph.name in overrides:
        raw = overrides[ph.name]
    elif env_var_name(ph.name) in os.environ:
        raw = os.environ[env_var_name(ph.name)]
    elif ph.name in os.environ:
        raw = os.environ[ph.name]
    elif ph.default is not None:
        raw = ph.default
    else:
        return None

    if ph.ptype == "path":
        return _validate_path(raw)
    return raw


def collect_values(
    placeholders: list[Placeholder],
    *,
    overrides: dict[str, str],
    cloud: bool,
) -> tuple[dict[str, str], set[str]]:
    values: dict[str, str] = {}
    secrets: set[str] = set()

    for ph in placeholders:
        if ph.secret:
            secrets.add(ph.name)

        try:
            prefilled = prefill_placeholder(ph, overrides)
        except ValueError as exc:
            print(f"xadabra: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc

        if prefilled is not None:
            values[ph.name] = prefilled
            continue

        if cloud:
            print(
                f"xadabra: cloud mode — missing {ph.name} "
                f"(set {env_var_name(ph.name)} or --set {ph.name}=...)",
                file=sys.stderr,
            )
            raise SystemExit(1)

        values[ph.name] = prompt_for_placeholder(ph)

    return values, secrets
