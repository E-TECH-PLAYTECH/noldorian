from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable


def read_clipboard() -> str:
    try:
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("xadabra: clipboard read failed (pbpaste)") from exc
    return result.stdout


def confirm_run(*, auto_yes: bool = False, cloud: bool = False) -> bool:
    if auto_yes or cloud:
        return True
    if not sys.stdin.isatty():
        print("xadabra: non-interactive — skipping Run? (use --yes to silence)", file=sys.stderr)
        return True
    answer = input("Run? [y/N] ").strip().lower()
    return answer in ("y", "yes")


def shell_command() -> list[str]:
    """Prefer zsh on macOS; bash elsewhere (Claude Code cloud is Linux)."""
    if shutil.which("zsh"):
        return ["zsh", "-c"]
    if shutil.which("bash"):
        return ["bash", "-c"]
    return ["sh", "-c"]


def execute_script(
    script: str,
    *,
    cwd: str | None = None,
    stream: Callable[[str], None] | None = None,
) -> int:
    cwd = cwd or os.getcwd()
    cmd = shell_command()
    proc = subprocess.Popen(
        [*cmd, script],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        if stream:
            stream(line)
        else:
            sys.stdout.write(line)
            sys.stdout.flush()
    return proc.wait()


# Back-compat alias
execute_zsh = execute_script
