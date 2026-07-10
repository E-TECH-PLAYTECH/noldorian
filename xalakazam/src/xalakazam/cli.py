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
SETUP_SCRIPT = """if [ -n "$NOLDORIAN_TOKEN" ]; then
  curl -fsSL -H "Authorization: Bearer $NOLDORIAN_TOKEN" \\
    -H "Accept: application/vnd.github.raw" \\
    https://api.github.com/repos/Everplay-Tech/noldorian/contents/bootstrap.sh \\
    | GITHUB_TOKEN="$NOLDORIAN_TOKEN" bash -s -- --all --spells || true
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


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(
            f"""xalakazam {__version__} — the Everplay orienter (callable memory)

  xalakazam --deploy      how to install + strategically use Noldorian
  xalakazam --spells      how to install + strategically use the snx spellbook
  xalakazam --bootstrap   copy-paste install one-liners (gh / GITHUB_TOKEN)
  xalakazam --setup-script  print + clipboard-copy the claude.ai environment
                          setup script (consumes NOLDORIAN_TOKEN at boot)
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
