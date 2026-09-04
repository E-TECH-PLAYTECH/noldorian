from __future__ import annotations

import argparse
import sys
from pathlib import Path

from xadabra import __version__
from xadabra.fills import collect_values, parse_set_args
from xadabra.history import append_run
from xadabra.parser import find_placeholders, substitute, substitute_for_run
from xadabra.policy import script_uses_spells
from xadabra.runner import confirm_run, execute_script, read_clipboard


def load_script(source: str | None, *, cloud: bool) -> tuple[str, str]:
    if source == "-":
        return sys.stdin.read(), "stdin"
    if source:
        path = Path(source)
        if path.is_file():
            return path.read_text(encoding="utf-8"), str(path)
        print(f"xadabra: file not found: {source}", file=sys.stderr)
        raise SystemExit(1)
    if cloud:
        print("xadabra: cloud mode needs a script file or stdin (-)", file=sys.stderr)
        raise SystemExit(1)
    return read_clipboard(), "clipboard"


def run_pipeline(
    script: str,
    *,
    source_label: str,
    dry_run: bool = False,
    auto_yes: bool = False,
    cloud: bool = False,
    overrides: dict[str, str] | None = None,
    allow_spells: bool = False,
) -> int:
    overrides = overrides or {}
    placeholders = find_placeholders(script)
    values: dict[str, str] = {}
    secrets: set[str] = set()
    if placeholders:
        values, secrets = collect_values(placeholders, overrides=overrides, cloud=cloud)

    preview = substitute(script, values, mask_secrets=secrets) if placeholders else script
    print("--- script preview ---")
    print(preview.rstrip())
    print("----------------------")

    if dry_run:
        print("xadabra: dry-run — not executing")
        return 0

    if not confirm_run(auto_yes=auto_yes, cloud=cloud):
        print("xadabra: cancelled")
        return 0

    runnable = substitute_for_run(script, values) if placeholders else script

    if cloud and not allow_spells and script_uses_spells(runnable):
        print(
            "xadabra: cloud policy blocks snx — spells run on the operator machine, not in cloud",
            file=sys.stderr,
        )
        print("xadabra: use plain shell in cloud scripts, or --allow-spells to override", file=sys.stderr)
        return 1

    append_run(
        runnable if not secrets else substitute(script, values, mask_secrets=secrets),
        source=source_label,
    )

    code = execute_script(runnable)
    if code == 0:
        print("✅ xadabra: finished (exit 0)")
    else:
        print(f"❌ xadabra: failed (exit {code})")
    return code


def main(argv: list[str] | None = None) -> int:
    from noldorian.vault import ensure_canonical_home

    ensure_canonical_home()
    argv = list(argv if argv is not None else sys.argv[1:])

    if argv and argv[0] in ("--version", "-V", "version"):
        print(f"xadabra {__version__}")
        return 0

    if argv and argv[0] == "noldorian":
        from xadabra.noldorian import main as noldorian_main

        return noldorian_main(argv[1:])

    parser = argparse.ArgumentParser(
        prog="xadabra",
        description="Paste-once runner for AI shell blocks with {{placeholders}}",
    )
    parser.add_argument("source", nargs="?", default=None, help="file path, - for stdin, or clipboard")
    parser.add_argument("--yes", "-y", action="store_true", help="skip Run? confirmation")
    parser.add_argument("--dry-run", action="store_true", help="preview only, do not execute")
    parser.add_argument(
        "--cloud",
        action="store_true",
        help="cloud/CI mode: no clipboard/prompts; require --set or XADABRA_* env vars",
    )
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="NAME=value",
        help="placeholder value (repeatable); also reads XADABRA_NAME env",
    )
    parser.add_argument(
        "--allow-spells",
        action="store_true",
        help="cloud only: allow snx in scripts (default: blocked)",
    )
    args = parser.parse_args(argv)

    try:
        overrides = parse_set_args(args.set)
    except ValueError as exc:
        print(f"xadabra: {exc}", file=sys.stderr)
        return 1

    try:
        script, label = load_script(args.source, cloud=args.cloud)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    if not script.strip():
        print("xadabra: empty script", file=sys.stderr)
        return 1

    return run_pipeline(
        script,
        source_label=label,
        dry_run=args.dry_run,
        auto_yes=args.yes,
        cloud=args.cloud,
        overrides=overrides,
        allow_spells=args.allow_spells,
    )


if __name__ == "__main__":
    raise SystemExit(main())
