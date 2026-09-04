from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from binabra import __version__, anchor_sh_path, discover_bin


def _legacy_exec(argv: list[str]) -> int:
    bin_dir = discover_bin()
    if bin_dir is None:
        print("abra: no bin directory found", file=sys.stderr)
        return 1
    target = bin_dir / argv[0]
    if not target.exists():
        print(f"abra: not found: {target}", file=sys.stderr)
        return 1
    os.execv(str(target), [str(target), *argv[1:]])


def main(argv: list[str] | None = None) -> int:
    from noldorian.vault import ensure_canonical_home

    ensure_canonical_home()
    argv = list(argv if argv is not None else sys.argv[1:])

    if not argv or argv[0] in ("--dir", "dir"):
        found = discover_bin()
        if found is None:
            print("abra: no bin directory found", file=sys.stderr)
            return 1
        print(found)
        return 0

    if argv[0] in ("-h", "--help", "help"):
        print(
            """abra — portable bin-directory anchor (binabra)

  source "$(abra sh)"              portable header (any script, anywhere)
  abra embed                       print that one-liner
  abra sh                          path to anchor.sh
  abra dir [--here PATH]           discover or resolve bin directory
  abra exec <tool> [args...]       run sibling from discovered bin
  abra init [project-dir]          create bin/abra in a project
  abra colocate [dest-dir]         copy abra into a bin folder
  abra <tool> [args...]            legacy: run sibling (same as exec)

  python3 -m pip install noldorian
"""
        )
        return 0

    if argv[0] in ("--version", "-V", "version"):
        print(f"binabra {__version__}")
        return 0

    if argv[0] == "sh":
        print(anchor_sh_path())
        return 0

    if argv[0] == "embed":
        print('source "$(abra sh)"')
        return 0

    if argv[0] == "exec":
        if len(argv) < 2:
            print("usage: abra exec <command> [args...]", file=sys.stderr)
            return 1
        return _legacy_exec(argv[1:])

    if argv[0] == "colocate":
        dest = Path(argv[1] if len(argv) > 1 else "bin").expanduser().resolve()
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / "abra"
        shutil.copy2(anchor_sh_path(), target)
        target.chmod(target.stat().st_mode | 0o111)
        print(target)
        return 0

    if argv[0] == "init":
        root = Path(argv[1] if len(argv) > 1 else ".").expanduser().resolve()
        bin_dir = root / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        target = bin_dir / "abra"
        shutil.copy2(anchor_sh_path(), target)
        target.chmod(target.stat().st_mode | 0o111)
        (root / ".abra").mkdir(exist_ok=True)
        print(f"initialized {bin_dir}")
        print('use: source "$(dirname "${BASH_SOURCE[0]}")/abra"')
        return 0

    if argv[0] == "dir":
        if len(argv) > 1 and argv[1] == "--here":
            if len(argv) < 3:
                print("usage: abra dir --here PATH", file=sys.stderr)
                return 1
            print(Path(argv[2]).expanduser().resolve().parent)
            return 0
        found = discover_bin()
        if found is None:
            print("abra: no bin directory found", file=sys.stderr)
            return 1
        print(found)
        return 0

    return _legacy_exec(argv)


if __name__ == "__main__":
    raise SystemExit(main())
