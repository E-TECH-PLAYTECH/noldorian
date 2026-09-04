"""Pip-only helper for the unified public Noldorian package."""

from __future__ import annotations

import argparse
import subprocess
import sys
import textwrap

PYPI_PACKAGE = "noldorian"
PYPI_VERSION = "0.2.2"


def cmd_guide(_: argparse.Namespace) -> int:
    print(
        textwrap.dedent(
            f"""
            xadabra noldorian — public package helper
            =========================================

            The install is the unified public distribution:
              python3 -m pip install {PYPI_PACKAGE}
              # pin: python3 -m pip install {PYPI_PACKAGE}=={PYPI_VERSION}

            Then:
              noldorian doctor

            The first doctor run creates ~/.config/noldorian/vault.env.
            Fill names with: xabra env set NAME

            This helper does not clone GitHub, pack sibling packages, or publish.
            Install is always: python3 -m pip install noldorian
            """
        ).strip()
    )
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    spec = f"{PYPI_PACKAGE}=={PYPI_VERSION}"
    line = f"python3 -m pip install --user --force-reinstall {spec}"
    print(line)
    if args.run:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--user",
                "--force-reinstall",
                spec,
            ]
        ).returncode
    return 0


def cmd_script(args: argparse.Namespace) -> int:
    text = (
        f"python3 -m pip install {PYPI_PACKAGE}\n"
        "noldorian doctor\n"
        "xabra env set NAME\n"
    )
    if args.print_path:
        print("pip-install noldorian (no private template file)")
        return 0
    print(text, end="")
    if args.copy:
        subprocess.run(["pbcopy"], input=text, text=True, check=False)
        print("# copied to clipboard", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="xadabra noldorian",
        description="Print or run the public pip install for Noldorian",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("guide", help="print walkthrough checklist")
    p.set_defaults(func=cmd_guide)

    p = sub.add_parser("install", help="print the unified noldorian install command")
    p.add_argument("--run", action="store_true", help="run pip install")
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("script", help="emit a pip + doctor paste block")
    p.add_argument("--copy", action="store_true", help="copy template to clipboard (pbcopy)")
    p.add_argument("--path", action="store_true", dest="print_path")
    p.set_defaults(func=cmd_script)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
