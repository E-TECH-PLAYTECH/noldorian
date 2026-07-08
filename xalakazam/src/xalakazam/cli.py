from __future__ import annotations

import sys

from xalakazam import BOOTSTRAP_HINT, DEPLOY, SPELLS, __version__


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(
            f"""xalakazam {__version__} — the Everplay orienter (callable memory)

  xalakazam --deploy      how to install + strategically use Noldorian
  xalakazam --spells      how to install + strategically use the snx spellbook
  xalakazam --bootstrap   copy-paste install one-liners (gh / GITHUB_TOKEN)
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

    if argv[0] == "--all":
        print(DEPLOY)
        print()
        print(SPELLS)
        return 0

    print(f"xalakazam: unknown flag '{argv[0]}' (try --deploy / --spells)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
