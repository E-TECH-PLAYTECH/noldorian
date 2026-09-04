"""xabra — Noldorian operator CLI (vault subcommands + verified-install flags)."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from xabra import __version__, load_registry
from xabra.core import (
    APPLICATIONS,
    bank_receipt,
    dmg_embedded_info,
    emit,
    fetch,
    install_cli,
    install_dmg_app,
    installed_app_info,
    protocol_info,
    repoint_protocol,
    resolve_source,
    sh,
)


def _pick_app(apps: dict, name: str | None) -> tuple[str, dict]:
    if not name:
        raise SystemExit("xabra: this action needs --app <name> (see --list)")
    if name not in apps:
        raise SystemExit(f"xabra: unknown app '{name}' — known: {', '.join(sorted(apps))}")
    return name, apps[name]


def _confirm(prompt: str, yes: bool) -> None:
    if yes:
        return
    if not sys.stdin.isatty():
        raise SystemExit("xabra: refusing to install without --yes in a non-interactive session")
    if input(f"{prompt} [y/N] ").strip().lower() not in ("y", "yes"):
        raise SystemExit("xabra: aborted")


def _digits(text: str | None) -> int | None:
    if not text:
        return None
    hits = re.findall(r"\d+", text)
    return int(hits[-1]) if hits else None


def newer_available(installed: dict, source: dict) -> bool:
    """Honest comparison: build numbers when we can get them, else difference counts."""
    if not installed.get("installed"):
        return bool(source)
    if not source:
        return False
    have = _digits(installed.get("build") or installed.get("version"))
    if source["type"] == "local" and source["resolved"].endswith(".dmg"):
        probe = dmg_embedded_info(Path(source["resolved"]))
        want = _digits(probe.get("build") or probe.get("version"))
        if have is not None and want is not None:
            return want > have
        return False  # unreadable dmg — don't churn installs on a guess
    want = _digits(source.get("resolved"))
    if have is not None and want is not None:
        return want > have
    return True  # can't compare — surface it as updatable, install verifies


# ---------------------------------------------------------------- actions

def act_list(apps: dict, as_json: bool) -> int:
    rows = {name: {**installed_app_info(spec), "kind": spec["kind"], "repo": spec.get("repo")}
            for name, spec in apps.items()}
    if as_json:
        json.dump(rows, sys.stdout, indent=2)
        print()
        return 0
    if not rows:
        print("xabra: no apps in the operator registry (default is empty).")
        print("  add entries to ~/.config/noldorian/apps.json")
        return 0
    for name, row in sorted(rows.items()):
        mark = row.get("version") or ("installed" if row.get("installed") else "not installed")
        build = f" ({row['build']})" if row.get("build") else ""
        print(f"{name:12} {row['kind']:4} {mark}{build}   {row.get('repo') or ''}")
    return 0


def act_status(apps: dict, name: str | None, as_json: bool) -> int:
    name, spec = _pick_app(apps, name)
    installed = installed_app_info(spec)
    source = resolve_source(spec)
    receipt = {
        "action": "status", "app": name, "ok": True,
        "installed": installed, "available": source or None,
        "update_available": newer_available(installed, source),
    }
    proto = protocol_info(spec)
    if proto:
        receipt["protocol"] = proto
    emit(receipt, as_json)
    return 0


def act_protocol_update(apps: dict, name: str | None, yes: bool, as_json: bool) -> int:
    name, spec = _pick_app(apps, name)
    if not spec.get("protocol"):
        raise SystemExit(f"xabra: '{name}' declares no protocol binary")
    receipt: dict = {"action": "protocol-update", "app": name, "ok": False}
    info = protocol_info(spec)
    if info["drift"]:
        _confirm(
            f"xabra: point MCP '{info['mcp_name']}' at {info['app_bin']} "
            f"(was {info.get('enrolled_command')})?", yes)
    try:
        repoint_protocol(spec, receipt)
    finally:
        receipt["receipt"] = str(bank_receipt(receipt))
        emit(receipt, as_json)
    return 0 if receipt["ok"] else 1


def act_install(apps: dict, name: str | None, dmg: str | None, yes: bool,
                as_json: bool, only_if_newer: bool = False) -> int:
    name, spec = _pick_app(apps, name)
    receipt: dict = {"action": "update" if only_if_newer else "install", "app": name, "ok": False}
    installed = installed_app_info(spec)

    if dmg:
        source = {"type": "local", "resolved": str(Path(dmg).expanduser())}
    else:
        source = resolve_source(spec)
        if not source:
            receipt["error"] = "no source resolves — publish a release/artifact or pass --dmg"
            receipt["receipt"] = str(bank_receipt(receipt))
            emit(receipt, as_json)
            return 1
        if only_if_newer and not newer_available(installed, source):
            receipt.update(ok=True, skipped="already current",
                           installed=installed, available=source)
            emit(receipt, as_json)
            return 0
    receipt["source"] = source

    _confirm(f"xabra: install {name} from {source.get('resolved')}?", yes)
    workdir = Path(tempfile.mkdtemp(prefix="xabra-"))
    try:
        payload = fetch(source, workdir)
        if spec["kind"] == "cli":
            install_cli(spec, payload, receipt)
        else:
            install_dmg_app(spec, payload, receipt)
        receipt.update(installed_app_info(spec))
        receipt["ok"] = True
        if spec.get("protocol"):
            proto_receipt: dict = {}
            repoint_protocol(spec, proto_receipt)
            receipt["protocol"] = proto_receipt.get("protocol_after")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        receipt["receipt"] = str(bank_receipt(receipt))
        emit(receipt, as_json)
    return 0 if receipt["ok"] else 1


def act_update_all(apps: dict, yes: bool, as_json: bool) -> int:
    worst = 0
    for name in sorted(apps):
        try:
            worst = max(worst, act_install(apps, name, None, yes, as_json, only_if_newer=True))
        except SystemExit as exc:
            print(f"xabra: {name}: {exc}", file=sys.stderr)
            worst = 1
    return worst


def act_open(apps: dict, name: str | None, as_json: bool) -> int:
    name, spec = _pick_app(apps, name)
    installed = installed_app_info(spec)
    receipt = {"action": "open", "app": name, "ok": False, "installed": installed}
    if not installed.get("installed"):
        receipt["error"] = "not installed — run --install first"
    elif spec["kind"] == "cli":
        receipt.update(ok=True, note=f"CLI — run `{spec['bin']}` directly", path=installed["path"])
    else:
        out = sh(["open", str(APPLICATIONS / spec["app"])])
        receipt["ok"] = out.returncode == 0
        if out.returncode != 0:
            receipt["error"] = out.stderr.strip()
    emit(receipt, as_json)
    return 0 if receipt["ok"] else 1


def act_doctor(as_json: bool) -> int:
    from noldorian.doctor import doctor_report

    report = doctor_report()
    checks: dict = {"doctor": report}
    if sys.platform == "darwin":
        checks["macos_tools"] = {
            tool: shutil.which(tool) or "MISSING"
            for tool in ("hdiutil", "spctl", "codesign", "ditto")
        }
    checks["gh"] = shutil.which("gh")
    emit({"action": "doctor", "app": "-", "ok": bool(report.get("ok")), "checks": checks}, as_json)
    return 0 if report.get("ok") else 1


# ---------------------------------------------------------------- entry

OPERATOR_COMMANDS = {"run", "env", "pypi", "copy", "macos-keychain"}


def main(argv: list[str] | None = None) -> int:
    raw = list(argv if argv is not None else sys.argv[1:])
    if raw and raw[0] in OPERATOR_COMMANDS:
        from xabra.operator import main as operator_main

        return operator_main(raw)
    if not raw or raw[0] in ("-h", "--help", "help"):
        from xabra.operator import help_text

        print(help_text())
        return 0
    if raw[0] in ("--version", "-V", "version"):
        print(f"xabra {__version__}")
        return 0

    ap = argparse.ArgumentParser(
        prog="xabra",
        description="Noldorian operator CLI: vault subcommands or verified-install flags.")
    ap.add_argument("--app", metavar="NAME", help="target app (see --list)")
    action = ap.add_mutually_exclusive_group()
    action.add_argument("--list", action="store_true", help="known apps + installed state")
    action.add_argument("--status", action="store_true", help="installed vs latest available")
    action.add_argument("--install", action="store_true", help="fetch, verify, install latest")
    action.add_argument("--update", action="store_true", help="install only if newer resolves")
    action.add_argument("--open", action="store_true", help="open the installed app")
    action.add_argument("--doctor", action="store_true", help="install / vault / tools (broker optional)")
    ap.add_argument("--all", action="store_true", help="with --update: every known app")
    ap.add_argument("--protocol", action="store_true",
                    help="with --update: repoint the app's MCP enrollment at the installed binary")
    ap.add_argument("--dmg", metavar="PATH", help="install from this local dmg/tar.gz")
    ap.add_argument("--yes", action="store_true", help="skip the confirm prompt")
    ap.add_argument("--json", action="store_true", help="print the receipt as JSON")
    ap.add_argument("--version", action="version", version=f"xabra {__version__}")
    args = ap.parse_args(raw)

    apps = load_registry()
    if args.list or (not args.app and not any(
            (args.status, args.install, args.update, args.open, args.doctor))):
        return act_list(apps, args.json)
    if args.doctor:
        return act_doctor(args.json)
    if args.install:
        return act_install(apps, args.app, args.dmg, args.yes, args.json)
    if args.update:
        if args.protocol:
            return act_protocol_update(apps, args.app, args.yes, args.json)
        if args.all:
            return act_update_all(apps, args.yes, args.json)
        return act_install(apps, args.app, args.dmg, args.yes, args.json, only_if_newer=True)
    if args.open:
        return act_open(apps, args.app, args.json)
    return act_status(apps, args.app, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
