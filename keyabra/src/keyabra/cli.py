from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from keyabra import (
    ENV_DIR,
    __version__,
    find_dist_files,
    load_env_file,
    probe_env_file,
    prompt_secret,
    run_with_env,
)
from keyabra.cursor_gcp import (
    CursorApiKeyError,
    store_cursor_api_key_in_gcp,
)
from keyabra.cursor_gcp import (
    SecretStoreError as CursorSecretStoreError,
)
from keyabra.discord_gcp import (
    DiscordTokenError,
    SecretStoreError,
    store_discord_token_in_gcp,
)


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
    print("  python3 -m pip install --user build twine", file=sys.stderr)
    raise SystemExit(1)


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
        print(f"keyabra: unexpected arg '{argv[i]}'", file=sys.stderr)
        return 1

    if not env_names and not env_files:
        print(
            "usage: keyabra run [--env-file PATH ...] [--env NAME ...] -- <command> [args...]",
            file=sys.stderr,
        )
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
    # Vault files first (no prompting), then interactive --env on top.
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
            print(f"keyabra: {exc}", file=sys.stderr)
            return 1
    for name in env_names:
        env_vars[name] = prompt_secret(name)

    return run_with_env(command, env_vars)


def _cmd_env(argv: list[str]) -> int:
    """Owner-side vault management: init / set / set-file / list."""
    sub = argv[0] if argv else "list"
    default_vault = ENV_DIR / "keyabra.env"

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
            l for l in lines if not (l.split("=", 1)[0].strip() in (key,) and "=" in l)
        ]
        lines.append(f"{name}={rhs}")
        p.write_text("\n".join(lines) + "\n")
        os.chmod(p, 0o600)
        print(f"keyabra: {key} set in {p}")

    if sub == "init":
        p = vault_path(argv[1:])
        ensure_vault(p)
        print(f"keyabra: vault ready at {p} (0600)")
        return 0

    if sub == "set" and len(argv) >= 2:
        p = vault_path(argv[2:])
        value = prompt_secret(argv[1])
        upsert(p, argv[1], value)
        return 0

    if sub == "set-file" and len(argv) >= 3:
        # Store a POINTER to the file (NAME__FILE=path) — the secret material
        # stays where it already lives; run-time resolution reads it fresh.
        p = vault_path(argv[3:])
        target = Path(argv[2]).expanduser().resolve()
        if not target.is_file():
            print(f"keyabra: no such file: {target}", file=sys.stderr)
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
            print(f"keyabra: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    if sub == "list":
        p = vault_path(argv[1:])
        if not p.is_file():
            print(f"keyabra: no vault at {p}")
            return 0
        names = [
            line.split("=", 1)[0].strip()
            for line in p.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#") and "=" in line
        ]
        print(f"{p}:")
        for n in names:
            print(f"  {n}")
        return 0

    print(
        "usage:\n"
        "  keyabra env init [--file PATH]\n"
        "  keyabra env set NAME [--file PATH]           prompt -> store value\n"
        "  keyabra env set-file NAME /path [--file PATH]  store NAME__FILE pointer\n"
        "  keyabra env probe NAME [--file PATH]         validate without disclosure\n"
        "  keyabra env list [--file PATH]               names only, never values",
        file=sys.stderr,
    )
    return 1


def _concealed_copy_macos(value: str) -> bool:
    """Write the clipboard with org.nspasteboard.ConcealedType alongside plain
    text, so clipboard-history managers that honor the nspasteboard.org
    convention skip the entry. The secret travels via stdin — never argv.
    Returns False (caller falls back to pbcopy) if the NSPasteboard path fails.

    Honest limits: ConcealedType is a convention, not protection — a hostile
    pasteboard reader ignores it, and Universal Clipboard/Handoff can still
    sync the copy to other devices on the same iCloud account. The TTL
    auto-clear remains the control that actually holds.
    """
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
    """Vault -> system clipboard. The value is never displayed, never on argv,
    and auto-clears after --ttl seconds (only if the clipboard still holds it —
    a newer copy is never clobbered)."""
    name = argv[0] if argv and not argv[0].startswith("--") else None
    if not name:
        print(
            "usage: keyabra copy NAME [--file PATH] [--ttl SECONDS] [--env-line]\n"
            "  copies the vault entry to the clipboard without displaying it;\n"
            "  auto-clears after TTL (default 45s; --ttl 0 disables).\n"
            "  --env-line copies 'NAME=value' (for .env-format fields, e.g.\n"
            "  the claude.ai environment-variables box)",
            file=sys.stderr,
        )
        return 1

    vault = ENV_DIR / "keyabra.env"
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
                    f"keyabra: --ttl wants an integer, got {rest[i + 1]!r}",
                    file=sys.stderr,
                )
                return 1
            i += 2
        else:
            print(f"keyabra: unexpected arg '{rest[i]}'", file=sys.stderr)
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
        print(f"keyabra: {exc}", file=sys.stderr)
        return 1
    if name not in secrets:
        print(
            f"keyabra: no '{name}' in {vault} (keyabra env list shows names)",
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
        print("keyabra: no clipboard tool (pbcopy/wl-copy/xclip)", file=sys.stderr)
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
        f"keyabra: {name} on clipboard{line_note} ({len(value)} chars{concealed_note}{ttl_note})"
    )

    if ttl:
        # Detached watcher: gets the value on stdin (never argv), sleeps, and
        # clears the clipboard only if it still holds this exact value.
        watcher = (
            "import subprocess,sys,time\n"
            "v=sys.stdin.buffer.read()\n"
            f"time.sleep({ttl})\n"
            f"cur=subprocess.run({paste_cmd!r},capture_output=True).stdout\n"
            "if cur==v:\n"
            f"    subprocess.run({copy_cmd!r},input=b'')\n"
        )
        p = subprocess.Popen(
            [sys.executable, "-c", watcher],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        assert p.stdin is not None
        p.stdin.write(value.encode())
        p.stdin.close()
    return 0


def _cmd_pypi(argv: list[str]) -> int:
    sub = argv[0] if argv else "upload"

    if sub == "upload":
        paths = [p for p in argv[1:] if p != "--skip-build"]
        if not paths:
            paths = find_dist_files(Path.cwd())
            if not paths:
                print(
                    "keyabra: no dist/ files — run from project root or pass paths",
                    file=sys.stderr,
                )
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

    if sub == "yank-all":
        reason = "Moved to private GitHub: https://github.com/Everplay-Tech/noldorian"
        releases = [
            ("binabra", "0.1.0"),
            ("binabra", "0.1.1"),
            ("keyabra", "0.1.0"),
            ("keyabra", "0.1.1"),
            ("xadabra", "0.1.0"),
            ("xadabra", "0.1.1"),
        ]
        twine = _require("twine")
        token = prompt_secret("PyPI token (pypi-...)")
        for pkg, ver in releases:
            print(f"keyabra: yanking {pkg} {ver} ...")
            rc = run_with_env(
                [twine, "yank", pkg, ver, "-y", "--reason", reason],
                {"TWINE_USERNAME": "__token__", "TWINE_PASSWORD": token},
            )
            if rc != 0:
                return rc
        print("keyabra: all Noldorian public releases yanked")
        return 0

    if sub == "yank":
        if len(argv) < 3:
            print(
                "usage: keyabra pypi yank <package> <version> [version...]",
                file=sys.stderr,
            )
            return 1
        pkg = argv[1]
        versions = argv[2:]
        reason = "Moved to private GitHub: https://github.com/Everplay-Tech/noldorian"
        twine = _require("twine")
        token = prompt_secret("PyPI token (pypi-...)")
        for ver in versions:
            print(f"keyabra: yanking {pkg} {ver} ...")
            rc = run_with_env(
                [twine, "yank", pkg, ver, "-y", "--reason", reason],
                {"TWINE_USERNAME": "__token__", "TWINE_PASSWORD": token},
            )
            if rc != 0:
                return rc
        return 0

    print("usage:", file=sys.stderr)
    print("  keyabra pypi upload [dist/files...]", file=sys.stderr)
    print("  keyabra pypi publish [project-dir] [--skip-build]", file=sys.stderr)
    print(
        "  keyabra pypi yank-all              yank all public Noldorian releases",
        file=sys.stderr,
    )
    print(
        "  keyabra pypi yank <pkg> <ver>...   yank specific release(s)", file=sys.stderr
    )
    return 1


def _cmd_discord(argv: list[str]) -> int:
    sub = argv[0] if argv else ""
    if sub != "gcp-store":
        print(
            "usage: keyabra discord gcp-store --project PROJECT --secret NAME "
            "--guild-id ID [--application-id ID]",
            file=sys.stderr,
        )
        return 1

    values: dict[str, str] = {}
    args = argv[1:]
    allowed = {"--project", "--secret", "--guild-id", "--application-id"}
    i = 0
    while i < len(args):
        if args[i] not in allowed or i + 1 >= len(args):
            print(
                f"keyabra: unexpected or incomplete argument '{args[i]}'",
                file=sys.stderr,
            )
            return 1
        values[args[i][2:].replace("-", "_")] = args[i + 1]
        i += 2

    missing = [
        name for name in ("project", "secret", "guild_id") if not values.get(name)
    ]
    if missing:
        print(
            "keyabra: missing required option(s): "
            + ", ".join(f"--{name.replace('_', '-')}" for name in missing),
            file=sys.stderr,
        )
        return 1

    token = prompt_secret("Discord bot token", min_len=30)
    try:
        receipt = store_discord_token_in_gcp(
            token,
            project=values["project"],
            secret=values["secret"],
            guild_id=values["guild_id"],
            application_id=values.get("application_id"),
        )
    except (DiscordTokenError, SecretStoreError) as exc:
        print(f"keyabra: {exc}", file=sys.stderr)
        return 1
    finally:
        token = ""
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


def _cmd_cursor(argv: list[str]) -> int:
    sub = argv[0] if argv else ""
    if sub != "gcp-store":
        print(
            "usage: keyabra cursor gcp-store --project PROJECT --secret NAME",
            file=sys.stderr,
        )
        return 1

    values: dict[str, str] = {}
    args = argv[1:]
    allowed = {"--project", "--secret"}
    i = 0
    while i < len(args):
        if args[i] not in allowed or i + 1 >= len(args):
            print(
                f"keyabra: unexpected or incomplete argument '{args[i]}'",
                file=sys.stderr,
            )
            return 1
        values[args[i][2:].replace("-", "_")] = args[i + 1]
        i += 2

    missing = [name for name in ("project", "secret") if not values.get(name)]
    if missing:
        print(
            "keyabra: missing required option(s): "
            + ", ".join(f"--{name}" for name in missing),
            file=sys.stderr,
        )
        return 1

    api_key = prompt_secret("Cursor User API key", min_len=20)
    try:
        receipt = store_cursor_api_key_in_gcp(
            api_key,
            project=values["project"],
            secret=values["secret"],
        )
    except (CursorApiKeyError, CursorSecretStoreError) as exc:
        print(f"keyabra: {exc}", file=sys.stderr)
        return 1
    finally:
        api_key = ""
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(
            f"""keyabra {__version__} — prompt for secrets, run commands (no notepad dance)

  keyabra pypi publish [dir]         build → prompt token → twine upload
  keyabra pypi yank-all              yank public binabra/keyabra/xadabra 0.1.x
  keyabra pypi yank <pkg> <ver>...   yank specific release(s)
  keyabra run --env VAR -- cmd ...   prompt for secret(s) → run command
  keyabra run --env-file P -- cmd    load a 0600 env-vault → run command
  keyabra env init|set|set-file|probe|list manage the vault (~/.config/keyabra/)
  keyabra copy NAME [--ttl S]        vault -> clipboard, never displayed; auto-clears.
                                     macOS: marked ConcealedType (history managers skip
                                     it) — but Handoff/Universal Clipboard can still
                                     sync it to your other devices; the TTL is the
                                     control that holds
  keyabra discord gcp-store ...      hidden prompt → Discord preflight → GCP Secret
                                     Manager via stdin → readback + Discord postflight
  keyabra cursor gcp-store ...       hidden prompt → Cursor /v0/me preflight → GCP
                                     Secret Manager via stdin → readback + postflight

Vault lines: NAME=value · NAME__FILE=/path (contents at run time) ·
NAME__CMD=cmd (stdout at run time). Vault must be 0600 or keyabra refuses.

Examples:
  cd ~/Projects/binabra && keyabra pypi publish
  keyabra pypi upload dist/*
  keyabra run --env GITHUB_TOKEN -- gh release create ...
  keyabra env set-file ASC_API_KEY_P8 ~/Downloads/AuthKey_XXXX.p8
  keyabra run --env-file ~/.config/keyabra/keyabra.env -- ./deploy.sh

  pip install keyabra
"""
        )
        return 0

    if argv[0] in ("--version", "-V", "version"):
        print(f"keyabra {__version__}")
        return 0

    if argv[0] == "run":
        return _cmd_run(argv[1:])

    if argv[0] == "env":
        return _cmd_env(argv[1:])

    if argv[0] == "copy":
        return _cmd_copy(argv[1:])

    if argv[0] == "pypi":
        return _cmd_pypi(argv[1:])

    if argv[0] == "discord":
        return _cmd_discord(argv[1:])

    if argv[0] == "cursor":
        return _cmd_cursor(argv[1:])

    print(f"keyabra: unknown command '{argv[0]}' (try: keyabra help)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
