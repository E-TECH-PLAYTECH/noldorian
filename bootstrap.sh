#!/usr/bin/env bash
#
# Optional convenience installer for public Noldorian from PyPI.
# This script does not clone GitHub and does not require gh.
#
#   python3 -m pip install noldorian
# is the documented install. This file exists so an old curl-to-bash URL
# still lands on pip instead of a private spellbook clone.
set -euo pipefail

if [ "$#" -gt 0 ]; then
  echo "bootstrap: flags are unused. Install is always: python3 -m pip install noldorian" >&2
fi

PY="$(command -v python3)"
echo "== installing noldorian from PyPI (user site) =="
"$PY" -m pip install --user --quiet "noldorian>=0.2.3,<0.3" \
  && echo "  noldorian: ok" \
  || { echo "  noldorian: FAILED" >&2; exit 1; }

USER_BIN="$("$PY" -m site --user-base)/bin"
case ":$PATH:" in
  *":$USER_BIN:"*) ;;
  *) echo "== NOTE: add to PATH: export PATH=\"$USER_BIN:\$PATH\" ==" ;;
esac

echo
echo "== done. orient yourself: =="
echo "   $USER_BIN/noldorian doctor"
echo "   $USER_BIN/xalakazam --deploy"
