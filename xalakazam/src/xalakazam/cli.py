from __future__ import annotations

import shutil
import subprocess
import sys

from xalakazam import BOOTSTRAP_HINT, DEPLOY, OWNER_ACTIONS, SPELLS, __version__

SETUP_SCRIPT = """python3 -m pip install -q noldorian || true
"""


def _clipboard_copy(text: str) -> bool:
    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=text.encode(), check=True)
                return True
            except Exception:
                return False
    return False


def _open_url(url: str) -> None:
    opener = "open" if shutil.which("open") else ("xdg-open" if shutil.which("xdg-open") else None)
    if opener:
        subprocess.run([opener, url], check=False)


def _wait(prompt: str) -> None:
    if sys.stdin.isatty():
        input(prompt)
    else:
        print(prompt + " [no TTY — continuing]")


def _cmd_enable(argv: list[str]) -> int:
    """Copy-and-open walker for an environment that needs a vault token line."""

    repo = None
    url = ""
    vault_args: list[str] = []
    no_open = False
    i = 0
    while i < len(argv):
        if argv[i] == "--url" and i + 1 < len(argv):
            url = argv[i + 1]
            i += 2
        elif argv[i] == "--vault" and i + 1 < len(argv):
            vault_args = ["--file", argv[i + 1]]
            i += 2
        elif argv[i] == "--no-open":
            no_open = True
            i += 1
        elif not argv[i].startswith("--") and repo is None:
            repo = argv[i]
            i += 1
        else:
            print(f"xalakazam: unexpected arg '{argv[i]}'", file=sys.stderr)
            return 1

    xabra = shutil.which("xabra")
    if not xabra:
        print("xalakazam: xabra not on PATH — pip install noldorian, then rerun", file=sys.stderr)
        return 1
    if url and not no_open:
        _open_url(url)
    r = subprocess.run([xabra, "copy", "NOLDORIAN_TOKEN", "--ttl", "300", "--env-line", *vault_args])
    if r.returncode != 0:
        print(
            "xalakazam: NOLDORIAN_TOKEN is not in the vault — bank it first:\n"
            "  xabra env set NOLDORIAN_TOKEN",
            file=sys.stderr,
        )
        return 1
    _wait("Token line on clipboard (5-min TTL). Paste once, then Enter… ")
    return 0


def main(argv: list[str] | None = None) -> int:
    from noldorian.vault import ensure_canonical_home

    ensure_canonical_home()
    argv = list(argv if argv is not None else sys.argv[1:])

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(
            f"""xalakazam {__version__} — Noldorian orienter (callable memory)

  xalakazam --deploy         how to install + use Noldorian
  xalakazam --spells         Noldorian is not a spellbook; pip is the install path
  xalakazam --bootstrap      copy-paste install one-liners
  xalakazam --owner-actions  owner-only UI / purchase / secret checkpoint rite
  xalakazam --enable         vault token onto clipboard (xabra copy)
  xalakazam --setup-script   print a pip-install setup snippet
  xalakazam --all            deploy + spells + owner-actions
"""
        )
        return 0

    if argv[0] in ("--version", "-V", "version"):
        print(f"xalakazam {__version__}")
        return 0

    if argv[0] == "--deploy":
        print(DEPLOY)
        return 0

    if argv[0] == "--spells":
        print(SPELLS)
        return 0

    if argv[0] == "--bootstrap":
        print(BOOTSTRAP_HINT)
        return 0

    if argv[0] == "--owner-actions":
        print(OWNER_ACTIONS)
        return 0

    if argv[0] == "--enable":
        return _cmd_enable(argv[1:])

    if argv[0] == "--setup-script":
        print(SETUP_SCRIPT)
        if _clipboard_copy(SETUP_SCRIPT):
            print("\nxalakazam: setup script copied to clipboard", file=sys.stderr)
        return 0

    if argv[0] == "--all":
        print(DEPLOY)
        print()
        print(SPELLS)
        print()
        print(OWNER_ACTIONS)
        return 0

    print(f"xalakazam: unknown flag '{argv[0]}' (try --deploy / --bootstrap)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
