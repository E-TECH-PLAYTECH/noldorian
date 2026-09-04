"""Operator vault CLI: hidden prompt, 0600 vault, child env."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from noldorian.vault import (
    default_vault_path,
    list_vault_names,
    load_env_file,
    probe_env_file,
    prompt_secret,
    run_with_env,
)
from xabra import __version__

PROG = "xabra"


def _cmd_run(argv: list[str]) -> int:
    env_names: list[str] = []
    env_files: list[str] = []
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
        if argv[i] == "--env-file" and i + 1 < len(argv):
            env_files.append(argv[i + 1])
            i += 2
            continue
        if argv[i].startswith("--env-file="):
            env_files.append(argv[i].split("=", 1)[1])
            i += 1
            continue
        print(f"{PROG}: unexpected arg '{argv[i]}'", file=sys.stderr)
        return 1

    if not env_names and not env_files:
        print(
            f"usage: {PROG} run [--env-file PATH ...] [--env NAME ...] -- <command> [args...]",
            file=sys.stderr,
        )
        return 1

    try:
        sep = argv.index("--")
    except ValueError:
        print(f"{PROG}: missing -- before command", file=sys.stderr)
        return 1

    command = argv[sep + 1 :]
    if not command:
        print(f"{PROG}: missing command after --", file=sys.stderr)
        return 1

    env_vars: dict[str, str] = {}
    for f in env_files:
        try:
            env_vars.update(load_env_file(f))
        except (
            OSError,
            ValueError,
            RuntimeError,
            KeyError,
            subprocess.SubprocessError,
        ) as exc:
            print(f"{PROG}: {exc}", file=sys.stderr)
            return 1
    for name in env_names:
        env_vars[name] = prompt_secret(name)

    return run_with_env(command, env_vars)


def _cmd_env(argv: list[str]) -> int:
    sub = argv[0] if argv else "list"
    default_vault = default_vault_path()

    def vault_path(args: list[str]) -> Path:
        for j, a in enumerate(args):
            if a == "--file" and j + 1 < len(args):
                return Path(args[j + 1]).expanduser()
        return default_vault

    def ensure_vault(p: Path) -> None:
        p.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(p.parent, 0o700)
        if not p.exists():
            fd = os.open(p, os.O_WRONLY | os.O_CREAT, 0o600)
            os.close(fd)
        os.chmod(p, 0o600)

    def upsert(p: Path, name: str, rhs: str) -> None:
        ensure_vault(p)
        lines = p.read_text().splitlines()
        key = name.partition("=")[0]
        lines = [
            line
            for line in lines
            if not (line.split("=", 1)[0].strip() in (key,) and "=" in line)
        ]
        lines.append(f"{name}={rhs}")
        p.write_text("\n".join(lines) + "\n")
        os.chmod(p, 0o600)
        print(f"{PROG}: {key} set in {p}")

    if sub == "init":
        p = vault_path(argv[1:])
        ensure_vault(p)
        print(f"{PROG}: vault ready at {p} (0600)")
        return 0

    if sub == "set" and len(argv) >= 2:
        p = vault_path(argv[2:])
        value = prompt_secret(argv[1])
        upsert(p, argv[1], value)
        return 0

    if sub == "set-file" and len(argv) >= 3:
        p = vault_path(argv[3:])
        target = Path(argv[2]).expanduser().resolve()
        if not target.is_file():
            print(f"{PROG}: no such file: {target}", file=sys.stderr)
            return 1
        upsert(p, f"{argv[1]}__FILE", str(target))
        return 0

    if sub == "probe" and len(argv) >= 2:
        p = vault_path(argv[2:])
        try:
            receipt = probe_env_file(p, argv[1])
        except (
            OSError,
            ValueError,
            RuntimeError,
            KeyError,
            subprocess.SubprocessError,
        ) as exc:
            print(f"{PROG}: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    if sub == "list":
        p = vault_path(argv[1:])
        if not p.is_file():
            print(f"{PROG}: no vault at {p}")
            return 0
        try:
            names = list_vault_names(p)
        except (OSError, ValueError, PermissionError) as exc:
            print(f"{PROG}: {exc}", file=sys.stderr)
            return 1
        print(f"{p}:")
        for name in names:
            print(f"  {name}")
        return 0

    print(
        "usage:\n"
        f"  {PROG} env init [--file PATH]\n"
        f"  {PROG} env set NAME [--file PATH]           prompt -> store value\n"
        f"  {PROG} env set-file NAME /path [--file PATH]  store NAME__FILE pointer\n"
        f"  {PROG} env probe NAME [--file PATH]         validate without disclosure\n"
        f"  {PROG} env list [--file PATH]               names only, never values",
        file=sys.stderr,
    )
    return 1


def _concealed_copy_macos(value: str) -> bool:
    jxa = (
        'ObjC.import("AppKit");'
        "const d=$.NSFileHandle.fileHandleWithStandardInput.readDataToEndOfFile;"
        "const s=$.NSString.alloc.initWithDataEncoding(d,$.NSUTF8StringEncoding);"
        "const pb=$.NSPasteboard.generalPasteboard;"
        "pb.clearContents;"
        'pb.setStringForType(s,"org.nspasteboard.ConcealedType");'
        "pb.setStringForType(s,$.NSPasteboardTypeString);"
    )
    try:
        r = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", jxa],
            input=value.encode(),
            capture_output=True,
            timeout=10,
            check=False,
        )
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _cmd_copy(argv: list[str]) -> int:
    name = argv[0] if argv and not argv[0].startswith("--") else None
    if not name:
        print(
            f"usage: {PROG} copy NAME [--file PATH] [--ttl SECONDS] [--env-line]\n"
            "  copies the vault entry to the clipboard without displaying it;\n"
            "  auto-clears after TTL (default 45s; --ttl 0 disables).\n"
            "  --env-line copies 'NAME=value'",
            file=sys.stderr,
        )
        return 1

    vault = default_vault_path()
    ttl = 45
    env_line = False
    rest = argv[1:]
    i = 0
    while i < len(rest):
        if rest[i] == "--env-line":
            env_line = True
            i += 1
        elif rest[i] == "--file" and i + 1 < len(rest):
            vault = Path(rest[i + 1]).expanduser()
            i += 2
        elif rest[i] == "--ttl" and i + 1 < len(rest):
            try:
                ttl = max(0, int(rest[i + 1]))
            except ValueError:
                print(
                    f"{PROG}: --ttl wants an integer, got {rest[i + 1]!r}",
                    file=sys.stderr,
                )
                return 1
            i += 2
        else:
            print(f"{PROG}: unexpected arg '{rest[i]}'", file=sys.stderr)
            return 1

    try:
        secrets = load_env_file(vault)
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return 1
    if name not in secrets:
        print(
            f"{PROG}: no '{name}' in {vault} ({PROG} env list shows names)",
            file=sys.stderr,
        )
        return 1
    value = secrets[name]
    if env_line:
        value = f"{name}={value}"

    if shutil.which("pbcopy"):
        copy_cmd, paste_cmd = ["pbcopy"], ["pbpaste"]
    elif shutil.which("wl-copy"):
        copy_cmd, paste_cmd = ["wl-copy"], ["wl-paste", "-n"]
    elif shutil.which("xclip"):
        copy_cmd = ["xclip", "-selection", "clipboard"]
        paste_cmd = ["xclip", "-selection", "clipboard", "-o"]
    else:
        print(f"{PROG}: no clipboard tool (pbcopy/wl-copy/xclip)", file=sys.stderr)
        return 1

    concealed = False
    if copy_cmd == ["pbcopy"]:
        concealed = _concealed_copy_macos(value)
    if not concealed:
        subprocess.run(copy_cmd, input=value.encode(), check=True)
    ttl_note = f"; clears in {ttl}s if untouched" if ttl else "; auto-clear disabled"
    concealed_note = ", concealed" if concealed else ""
    line_note = " as NAME=value line" if env_line else ""
    print(
        f"{PROG}: {name} on clipboard{line_note} ({len(value)} chars{concealed_note}{ttl_note})"
    )

    if ttl:
        watcher = (
            "import subprocess,sys,time\n"
            "v=sys.stdin.buffer.read()\n"
            f"time.sleep({ttl})\n"
            f"cur=subprocess.run({paste_cmd!r},capture_output=True).stdout\n"
            "if cur==v:\n"
            f"    subprocess.run({copy_cmd!r},input=b'')\n"
        )
        proc = subprocess.Popen(
            [sys.executable, "-c", watcher],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        assert proc.stdin is not None
        proc.stdin.write(value.encode())
        proc.stdin.close()
    return 0


def _cmd_macos_keychain(argv: list[str]) -> int:
    from xabra.macos_keychain import MacOSKeychainError, unlock_keychain_from_vault

    sub = argv[0] if argv else ""
    usage = (
        f"usage: {PROG} macos-keychain unlock --env NAME --file VAULT "
        "[--keychain PATH] [--probe-identity HASH]"
    )
    if sub != "unlock":
        print(usage, file=sys.stderr)
        return 1

    values: dict[str, str] = {}
    args = argv[1:]
    allowed = {"--env", "--file", "--keychain", "--probe-identity"}
    i = 0
    while i < len(args):
        if args[i] not in allowed or i + 1 >= len(args):
            print(
                f"{PROG}: unexpected or incomplete argument '{args[i]}'",
                file=sys.stderr,
            )
            return 1
        values[args[i][2:].replace("-", "_")] = args[i + 1]
        i += 2

    missing = [name for name in ("env", "file") if not values.get(name)]
    if missing:
        print(
            f"{PROG}: missing required option(s): "
            + ", ".join(f"--{name}" for name in missing),
            file=sys.stderr,
        )
        print(usage, file=sys.stderr)
        return 1

    keychain = values.get(
        "keychain", str(Path.home() / "Library/Keychains/login.keychain-db")
    )
    try:
        receipt = unlock_keychain_from_vault(
            vault=values["file"],
            credential_name=values["env"],
            keychain=keychain,
            probe_identity=values.get("probe_identity"),
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        subprocess.SubprocessError,
        MacOSKeychainError,
    ) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


def help_text() -> str:
    return f"""{PROG} {__version__} — Noldorian operator CLI (vault + verified install)

Vault (paste-once, child env, no secret on argv):
  {PROG} run --env VAR -- cmd ...     prompt for secret(s) → run command
  {PROG} run --env-file P -- cmd      load a 0600 env-vault → run command
  {PROG} env init|set|set-file|probe|list
  {PROG} copy NAME [--ttl S]          vault -> clipboard, never displayed
  {PROG} macos-keychain unlock ...    0600 vault → in-process keychain unlock

Verified install (operator registry, default empty):
  {PROG} --list                       apps in ~/.config/noldorian/apps.json
  {PROG} --app NAME --install [--dmg PATH] [--yes]
  {PROG} --app NAME --status|--update|--open
  {PROG} --doctor                     install / vault / tools (no broker required)

Also: noldorian run …  and  noldorian doctor
"""


def main(argv: list[str] | None = None) -> int:
    from noldorian.vault import ensure_canonical_home

    ensure_canonical_home()
    argv = list(argv if argv is not None else sys.argv[1:])

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(help_text())
        return 0

    if argv[0] in ("--version", "-V", "version"):
        print(f"{PROG} {__version__}")
        return 0

    if argv[0] == "run":
        return _cmd_run(argv[1:])
    if argv[0] == "env":
        return _cmd_env(argv[1:])
    if argv[0] == "copy":
        return _cmd_copy(argv[1:])
    if argv[0] == "macos-keychain":
        return _cmd_macos_keychain(argv[1:])

    print(f"{PROG}: unknown command '{argv[0]}' (try: {PROG} help)", file=sys.stderr)
    return 1
