from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from keyabra import __version__, find_dist_files, prompt_secret, run_with_env


def _require(cmd: str) -> str:
    path = shutil.which(cmd)
    if path:
        return path
    # pip user scripts often live here on macOS
    for candidate in (
        Path.home() / "Library/Python/3.9/bin" / cmd,
        Path.home() / "Library/Python/3.10/bin" / cmd,
        Path.home() / "Library/Python/3.11/bin" / cmd,
        Path.home() / "Library/Python/3.12/bin" / cmd,
        Path.home() / ".local/bin" / cmd,
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    print(f"keyabra: '{cmd}' not found — install it first:", file=sys.stderr)
    print(f"  python3 -m pip install --user build twine", file=sys.stderr)
    raise SystemExit(1)


def _cmd_run(argv: list[str]) -> int:
    env_names: list[str] = []
    i = 0
    while i < len(argv) and argv[i] != "--":
        if argv[i] == "--env" and i + 1 < len(argv):
            env_names.append(argv[i + 1])
            i += 2
            continue
        if argv[i].startswith("--env="):
            env_names.append(argv[i].split("=", 1)[1])
            i += 1
            continue
        print(f"keyabra: unexpected arg '{argv[i]}'", file=sys.stderr)
        return 1

    if not env_names:
        print("usage: keyabra run --env NAME [--env NAME2 ...] -- <command> [args...]", file=sys.stderr)
        return 1

    try:
        sep = argv.index("--")
    except ValueError:
        print("keyabra: missing -- before command", file=sys.stderr)
        return 1

    command = argv[sep + 1 :]
    if not command:
        print("keyabra: missing command after --", file=sys.stderr)
        return 1

    env_vars: dict[str, str] = {}
    for name in env_names:
        env_vars[name] = prompt_secret(name)

    return run_with_env(command, env_vars)


def _cmd_pypi(argv: list[str]) -> int:
    sub = argv[0] if argv else "upload"

    if sub == "upload":
        paths = [p for p in argv[1:] if p != "--skip-build"]
        if not paths:
            paths = find_dist_files(Path.cwd())
            if not paths:
                print("keyabra: no dist/ files — run from project root or pass paths", file=sys.stderr)
                return 1

        twine = _require("twine")
        token = prompt_secret("PyPI token (pypi-...)")
        return run_with_env(
            [twine, "upload", *paths],
            {"TWINE_USERNAME": "__token__", "TWINE_PASSWORD": token},
        )

    if sub == "publish":
        args = [a for a in argv[1:] if a != "--skip-build"]
        project = Path(args[0] if args else ".").expanduser().resolve()
        skip_build = "--skip-build" in argv
        paths = find_dist_files(project)

        if not paths and not skip_build:
            print(f"keyabra: building {project} ...")
            rc = subprocess.run(
                [sys.executable, "-m", "build"],
                cwd=str(project),
                check=False,
            ).returncode
            if rc != 0:
                return rc
            paths = find_dist_files(project)

        if not paths:
            print(f"keyabra: nothing to upload in {project / 'dist'}", file=sys.stderr)
            return 1

        twine = _require("twine")
        token = prompt_secret("PyPI token (pypi-...)")
        print(f"keyabra: uploading {len(paths)} file(s) ...")
        return run_with_env(
            [twine, "upload", *paths],
            {"TWINE_USERNAME": "__token__", "TWINE_PASSWORD": token},
            cwd=project,
        )

    print("usage:", file=sys.stderr)
    print("  keyabra pypi upload [dist/files...]", file=sys.stderr)
    print("  keyabra pypi publish [project-dir] [--skip-build]", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(
            f"""keyabra {__version__} — prompt for secrets, run commands (no notepad dance)

  keyabra pypi publish [dir]         build → prompt token → twine upload
  keyabra pypi upload [files...]     prompt token → twine upload
  keyabra run --env VAR -- cmd ...   prompt for secret(s) → run command

Examples:
  cd ~/Projects/binabra && keyabra pypi publish
  keyabra pypi upload dist/*
  keyabra run --env GITHUB_TOKEN -- gh release create ...

  pip install keyabra
"""
        )
        return 0

    if argv[0] in ("--version", "-V", "version"):
        print(f"keyabra {__version__}")
        return 0

    if argv[0] == "run":
        return _cmd_run(argv[1:])

    if argv[0] == "pypi":
        return _cmd_pypi(argv[1:])

    print(f"keyabra: unknown command '{argv[0]}' (try: keyabra help)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
