#!/usr/bin/env bash
#
# bootstrap.sh — install Everplay Noldorian CLIs (and optionally the snx
# spellbook) on any machine or cloud container with bash + python3 + git.
#
# Auth: an authenticated `gh` CLI, or GITHUB_TOKEN/GH_TOKEN in the env.
#
#   with gh:            bash <(gh api -H "Accept: application/vnd.github.raw" \
#                         repos/Everplay-Tech/noldorian/contents/bootstrap.sh) [--all] [--spells]
#   with a token only:  curl -fsSL -H "Authorization: Bearer $GITHUB_TOKEN" \
#                         -H "Accept: application/vnd.github.raw" \
#                         https://api.github.com/repos/Everplay-Tech/noldorian/contents/bootstrap.sh \
#                         | bash -s -- --all
#
# Default: keyabra + xalakazam (the secrets tool and the orienter).
#   --all      also xadabra, binabra, xabra
#   --spells   also clone the snx spellbook to ~/spells + install the snx shim.
#              Cloud containers: cast freely — the container grimoire is
#              ephemeral, so EXPORT receipts before exit (receipts/ is
#              gitignored → everything in it is yours; new akashic events are
#              `git -C ~/spells diff -- akashic/events.jsonl`). Ship them in
#              your PR (receipts/<branch>/snax/) and/or POST to the INNERTUBE.
#              An unexported cast never happened.
set -euo pipefail

REPO="Everplay-Tech/noldorian"
SPELLS_REPO="Everplay-Tech/spells"
PKGS=(keyabra xalakazam)
WANT_SPELLS=0
for a in "$@"; do
  case "$a" in
    --all)    PKGS=(keyabra xalakazam xadabra binabra xabra) ;;
    --spells) WANT_SPELLS=1 ;;
    *) echo "bootstrap: unknown flag $a (valid: --all --spells)" >&2; exit 1 ;;
  esac
done

# --- auth -------------------------------------------------------------
TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
if [ -z "$TOKEN" ] && command -v gh >/dev/null 2>&1; then
  TOKEN="$(gh auth token 2>/dev/null || true)"
fi
if [ -z "$TOKEN" ]; then
  echo "bootstrap: no GitHub auth — set GITHUB_TOKEN or run 'gh auth login'" >&2
  exit 1
fi
URL="https://x-access-token:${TOKEN}@github.com/${REPO}.git"

# --- noldorian CLIs ----------------------------------------------------
PY="$(command -v python3)"
echo "== installing: ${PKGS[*]} (user site) =="
for p in "${PKGS[@]}"; do
  "$PY" -m pip install --user --quiet "git+${URL}#subdirectory=${p}" \
    && echo "  ${p}: ok" || { echo "  ${p}: FAILED" >&2; exit 1; }
done

USER_BIN="$("$PY" -m site --user-base)/bin"
case ":$PATH:" in
  *":$USER_BIN:"*) ;;
  *) echo "== NOTE: add to PATH: export PATH=\"$USER_BIN:\$PATH\" ==" ;;
esac

# --- spellbook (optional) ---------------------------------------------
if [ "$WANT_SPELLS" = 1 ]; then
  if [ ! -d "$HOME/spells/.git" ]; then
    echo "== cloning spellbook to ~/spells =="
    git clone --depth 1 "https://x-access-token:${TOKEN}@github.com/${SPELLS_REPO}.git" "$HOME/spells"
  else
    echo "== spellbook already at ~/spells =="
  fi
  mkdir -p "$HOME/bin"
  cat > "$HOME/bin/snx" <<'SH'
#!/bin/bash
# snx — global wrapper for the Snax CLI (installed by noldorian bootstrap)
exec /usr/bin/env PYTHONPATH="$HOME/spells/snax:${PYTHONPATH}" python3 -m snax.cli "$@"
SH
  chmod +x "$HOME/bin/snx"
  echo "== snx shim at ~/bin/snx (ensure ~/bin on PATH) =="
fi

echo
echo "== done. orient yourself: =="
echo "   $USER_BIN/xalakazam --deploy"
echo "   $USER_BIN/xalakazam --spells"
