"""Command-line interface for public Noldorian capability operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from noldorian import __version__
from noldorian.client import BrokerClient, DEFAULT_SOCKET_PATH
from noldorian.errors import BrokerError


def _json_object(value: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError("must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("must decode to a JSON object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="noldorian",
        description="Query and invoke agent-safe credential capabilities.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--socket",
        type=Path,
        default=DEFAULT_SOCKET_PATH,
        help="broker Unix socket (default: %(default)s)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="check broker readiness")
    commands.add_parser("list", help="list public credential capabilities")

    describe = commands.add_parser("describe", help="describe one capability")
    describe.add_argument("capability_id")

    invoke = commands.add_parser("invoke", help="invoke an approved capability operation")
    invoke.add_argument("capability_id")
    invoke.add_argument("operation")
    invoke.add_argument("--arguments-json", type=_json_object, default={})
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    client = BrokerClient(args.socket)
    try:
        if args.command == "status":
            result = client.status()
        elif args.command == "list":
            result = client.list_capabilities()
        elif args.command == "describe":
            result = client.describe(args.capability_id)
        else:
            result = client.invoke(
                args.capability_id,
                args.operation,
                args.arguments_json,
            )
    except (BrokerError, ValueError) as exc:
        print(f"noldorian: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
