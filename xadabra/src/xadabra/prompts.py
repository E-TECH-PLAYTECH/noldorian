from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path
from typing import Callable

from xadabra.parser import Placeholder, normalize_path_input


def _setup_readline_path_complete() -> None:
    try:
        import readline
    except ImportError:
        return

    def complete_path(text: str, state: int) -> str | None:
        expanded = os.path.expanduser(text or ".")
        parent = os.path.dirname(expanded) or "."
        base = os.path.basename(expanded)
        try:
            names = sorted(os.listdir(parent))
        except OSError:
            return None
        matches = [n for n in names if n.startswith(base)]
        if state >= len(matches):
            return None
        candidate = matches[state]
        full = os.path.join(parent, candidate)
        if os.path.isdir(full):
            return full + os.sep
        return full

    try:
        readline.set_completer_delims(" \t\n;")
        readline.parse_and_bind("tab: complete")
        readline.set_completer(complete_path)
    except Exception:
        pass


def prompt_for_placeholder(
    ph: Placeholder,
    *,
    input_func: Callable[[str], str] | None = None,
    secret_func: Callable[[str], str] | None = None,
) -> str:
    input_func = input_func or input
    secret_func = secret_func or getpass.getpass

    if ph.ptype == "path":
        _setup_readline_path_complete()

    while True:
        if ph.secret:
            value = secret_func(f"{ph.prompt_label}: ")
        else:
            if ph.default is not None:
                raw = input_func(f"{ph.prompt_label} [{ph.default}]: ")
                value = ph.default if raw == "" else raw
            else:
                value = input_func(f"{ph.prompt_label}: ")

        if ph.ptype == "path":
            value = normalize_path_input(value)
            path = Path(os.path.expanduser(value))
            if path.exists():
                return str(path)
            print(f"xadabra: path not found: {value}", file=sys.stderr)
            continue

        return value
