from __future__ import annotations

import shutil
import subprocess
import sys

from xalakazam import BOOTSTRAP_HINT, DEPLOY, SPELLS, __version__

# The claude.ai/code environment "setup script": runs at container start,
# before the agent wakes, consuming the NOLDORIAN_TOKEN env var so the ability
# layer (Noldorian CLIs + snx spellbook) is pre-installed. An env var alone
# does nothing by itself — this is what eats it. Paste into the environment
# configuration's setup-script field for ANY repo (it is repo-agnostic; only
# the env var is per-repo). `|| true` keeps a transient GitHub outage from
# bricking the container — the agent falls back to CLOUD_ABILITIES.md's
# manual block.
SETUP_SCRIPT = """if [ -f .claude/noldorian-bootstrap.sh ] && [ -n "$NOLDORIAN_TOKEN" ]; then
  GITHUB_TOKEN="$NOLDORIAN_TOKEN" bash .claude/noldorian-bootstrap.sh --all --spells || true
fi"""


def _clipboard_copy(text: str) -> bool:
    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=text.encode(), check=True)
                return True
            except Exception:
                return False
    return False


# Where claude.ai/code environment configuration lives. Verified 2026-07-09
# against code.claude.com/docs/en/claude-code-on-the-web#configure-your-environment:
# there is NO deep link — land on the app; the click path is the cloud icon
# (environment selector) -> hover the environment name -> settings icon, or
# "Add environment". Environments are WORKSPACE-scoped, not per-repo: one
# named environment (e.g. "everplay-abilities") serves every repo — you just
# select it when starting a session. Env vars are ONE .env-format text box
# (KEY=value lines); the setup script is its own field.
ENV_CONFIG_URL = "https://claude.ai/code"
CURSOR_API_KEY_URL = "https://cursor.com/dashboard/cloud-agents"
CLICK_PATH = (
    "click path: cloud icon (environment selector) -> hover the environment -> settings icon\n"
    "            (or 'Add environment'; environments are WORKSPACE-scoped — one serves every repo)"
)


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
    """The copy-and-open walker: enable ANY repo's claude.ai/code environment.

    Each step puts the right artifact on the clipboard and opens/points at the
    right surface; you paste, press Enter, next step. Nothing is ever displayed.
    """
    repo = None
    url = ENV_CONFIG_URL
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

    target = repo or "your workspace"
    print(f"xalakazam --enable: wiring the claude.ai/code environment ({target}).")
    print(f"Opening {url}\n{CLICK_PATH}\n")
    if not no_open:
        _open_url(url)

    # Step 1: the token, concealed, via keyabra (vault -> clipboard, TTL'd).
    keyabra = shutil.which("keyabra")
    if not keyabra:
        print("xalakazam: keyabra not on PATH — pip install it, then rerun", file=sys.stderr)
        return 1
    r = subprocess.run([keyabra, "copy", "NOLDORIAN_TOKEN", "--ttl", "300", "--env-line", *vault_args])
    if r.returncode != 0:
        print(
            "xalakazam: NOLDORIAN_TOKEN is not in the keyabra vault — bank it first:\n"
            "  keyabra env set NOLDORIAN_TOKEN",
            file=sys.stderr,
        )
        return 1
    _wait("STEP 1/2  'NOLDORIAN_TOKEN=…' line on clipboard (5-min TTL) — paste into the environment-variables box (.env format), one paste, done. Enter when pasted… ")

    # Step 2: the setup script.
    if not _clipboard_copy(SETUP_SCRIPT):
        print("xalakazam: no clipboard tool — copy the setup script from `xalakazam --setup-script`", file=sys.stderr)
        return 1
    _wait("STEP 2/2  setup script on clipboard — paste into the setup-script field, save. Enter when done… ")

    print(
        "\nDone. Every session started with this environment — ANY repo — now\n"
        "pre-installs the ability layer at container boot.\n"
        "Head-machine reminder (once per repo, stamps the covenant doc):\n"
        "  snx cloud-enable <repo-path> --ship\n"
        "Verify from any new web session: `command -v snx && snx list >/dev/null && echo ready`."
    )
    return 0


def _cmd_cursor_sdk_enable(argv: list[str]) -> int:
    """Open Cursor's key surface, then hand secure intake to Keyabra."""
    project = "everplay-centaur-chess"
    secret = "everplay-cursor-sdk-api-key"
    url = CURSOR_API_KEY_URL
    no_open = False
    i = 0
    while i < len(argv):
        if argv[i] == "--project" and i + 1 < len(argv):
            project = argv[i + 1]
            i += 2
        elif argv[i] == "--secret" and i + 1 < len(argv):
            secret = argv[i + 1]
            i += 2
        elif argv[i] == "--url" and i + 1 < len(argv):
            url = argv[i + 1]
            i += 2
        elif argv[i] == "--no-open":
            no_open = True
            i += 1
        else:
            print(f"xalakazam: unexpected arg '{argv[i]}'", file=sys.stderr)
            return 1

    keyabra = shutil.which("keyabra")
    if not keyabra:
        print("xalakazam: keyabra not on PATH — install it, then rerun", file=sys.stderr)
        return 1

    print("xalakazam: opening Cursor Cloud Agents → User API Keys.")
    print(f"Create a USER API key (not Admin and not a Models/BYOK key):\n  {url}")
    if not no_open:
        _open_url(url)
    _wait(
        "Create the key and copy it. Do not paste it into chat or a shell. "
        "Press Enter when it is on your clipboard… "
    )

    print(
        "Handing the credential directly to Keyabra's hidden prompt for live "
        "Cursor validation and GCP storage."
    )
    return subprocess.run(
        [
            keyabra,
            "cursor",
            "gcp-store",
            "--project",
            project,
            "--secret",
            secret,
        ],
        check=False,
    ).returncode


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(
            f"""xalakazam {__version__} — the Everplay orienter (callable memory)

  xalakazam --deploy      how to install + strategically use Noldorian
  xalakazam --spells      how to install + strategically use the snx spellbook
  xalakazam --bootstrap   copy-paste install one-liners (gh / GITHUB_TOKEN)
  xalakazam --enable [owner/repo]  the copy-and-open walker: wire ANY repo's
                          claude.ai/code environment — opens the surface, puts
                          token then setup script on the clipboard, one paste
                          per step ([--url U] [--vault P] [--no-open])
  xalakazam --setup-script  print + clipboard-copy the claude.ai environment
                          setup script (consumes NOLDORIAN_TOKEN at boot)
  xalakazam --cursor-sdk-enable  open Cursor User API Keys → Keyabra hidden
                          prompt → live validation → GCP Secret Manager
                          ([--project P] [--secret S] [--no-open])
  xalakazam --all         both playbooks

Say the word, know the world."""
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

    if argv[0] == "--enable":
        return _cmd_enable(argv[1:])

    if argv[0] == "--cursor-sdk-enable":
        return _cmd_cursor_sdk_enable(argv[1:])

    if argv[0] == "--setup-script":
        print(SETUP_SCRIPT)
        if _clipboard_copy(SETUP_SCRIPT):
            print("\nxalakazam: setup script copied to clipboard — paste into the claude.ai/code environment configuration's setup-script field (env var NOLDORIAN_TOKEN must also be set there)", file=sys.stderr)
        else:
            print("\nxalakazam: no clipboard tool found — copy the block above by hand", file=sys.stderr)
        return 0

    if argv[0] == "--all":
        print(DEPLOY)
        print()
        print(SPELLS)
        return 0

    print(f"xalakazam: unknown flag '{argv[0]}' (try --deploy / --spells)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
