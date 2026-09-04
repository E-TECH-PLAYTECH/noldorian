"""Command-line interface for public Noldorian operations."""

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
        description="Vault-aware operator CLI plus optional Gondolin extension client.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--socket",
        type=Path,
        default=DEFAULT_SOCKET_PATH,
        help="optional Gondolin Unix socket (default: %(default)s)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="install, vault, and extension status (no socket required)")
    commands.add_parser("status", help="check optional extension readiness")
    commands.add_parser("list", help="list public credential capabilities")
    commands.add_parser(
        "templates",
        help="list reviewed human enrollment templates",
    )

    describe = commands.add_parser("describe", help="describe one capability")
    describe.add_argument("capability_id")

    invoke = commands.add_parser("invoke", help="invoke an approved capability operation")
    invoke.add_argument("capability_id")
    invoke.add_argument("operation")
    invoke.add_argument("--arguments-json", type=_json_object, default={})

    enrollment = commands.add_parser(
        "request-enrollment",
        aliases=["enroll"],
        help="ask the owner-only enrollment prompt to create a capability",
    )
    enrollment.add_argument("template_id")
    enrollment.add_argument("--purpose", required=True, help="human-readable reason for access")
    enrollment.add_argument("--capability-id")
    enrollment.add_argument(
        "--operation",
        dest="operations",
        action="append",
        default=None,
        help="narrow the reviewed template operation set (repeatable)",
    )
    enrollment.add_argument("--resources-json", type=_json_object, default=None)

    status = commands.add_parser(
        "enrollment-status",
        help="check a human enrollment request without revealing a credential",
    )
    status.add_argument("request_id")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    raw_argv = list(argv if argv is not None else sys.argv[1:])
    family_commands = {
        "xadabra": ("xadabra.cli", "xadabra"),
        "xabra": ("xabra.cli", "xabra"),
        "abra": ("binabra.cli", "abra"),
        "binabra": ("binabra.cli", "binabra"),
        "xalakazam": ("xalakazam.cli", "xalakazam"),
    }
    if raw_argv and raw_argv[0] in family_commands:
        module_name, label = family_commands[raw_argv[0]]
        try:
            module = __import__(module_name, fromlist=["main"])
        except ImportError as exc:
            print(f"noldorian: bundled {label} surface is unavailable", file=sys.stderr)
            raise SystemExit(1) from exc
        return int(module.main(raw_argv[1:]))

    if raw_argv and raw_argv[0] in ("run", "env", "copy"):
        from xabra.operator import main as operator_main

        return int(operator_main(raw_argv))

    if raw_argv and raw_argv[0] == "doctor":
        from noldorian.doctor import doctor_report

        report = doctor_report()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    args = build_parser().parse_args(raw_argv)
    if args.command == "doctor":
        from noldorian.doctor import doctor_report

        report = doctor_report(socket_path=args.socket)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    client = BrokerClient(args.socket)
    try:
        if args.command == "status":
            result = client.status()
        elif args.command == "list":
            result = client.list_capabilities()
        elif args.command == "templates":
            result = client.list_enrollment_templates()
        elif args.command == "describe":
            result = client.describe(args.capability_id)
        elif args.command in {"request-enrollment", "enroll"}:
            result = client.request_enrollment(
                args.template_id,
                args.purpose,
                capability_id=args.capability_id,
                operations=args.operations,
                resources=args.resources_json,
            )
        elif args.command == "enrollment-status":
            result = client.enrollment_status(args.request_id)
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
