#!/usr/bin/env bash
#
# bootstrap.sh — install Everplay Noldorian CLIs (and optionally the snx
# spellbook) on any machine or cloud container with bash + python3 + git.
#
# Noldorian itself is public and needs no GitHub credential. `--spells` also
# clones the separate private spellbook and therefore requires authenticated
# `gh` (the GH_TOKEN/GITHUB_TOKEN environment variables are supported by gh).
#
#   curl -fsSL https://raw.githubusercontent.com/E-TECH-PLAYTECH/noldorian/main/bootstrap.sh \
#     | bash -s -- --all
#
# Default: the unified noldorian distribution (includes the family CLIs).
#   --all      compatibility alias; the same unified distribution is installed
#   --spells   also clone the snx spellbook to ~/spells + install the snx shim.
#              Cloud containers: cast freely — the container grimoire is
#              ephemeral, so EXPORT receipts before exit (receipts/ is
#              gitignored → everything in it is yours; new akashic events are
#              `git -C ~/spells diff -- akashic/events.jsonl`). Ship them in
#              your PR (receipts/<branch>/snax/) and/or POST to the INNERTUBE.
#              An unexported cast never happened.
set -euo pipefail

SPELLS_REPO="E-TECH-PLAYTECH/spells"
WANT_SPELLS=0
for a in "$@"; do
  case "$a" in
    --all)    : ;;
    --spells) WANT_SPELLS=1 ;;
    *) echo "bootstrap: unknown flag $a (valid: --all --spells)" >&2; exit 1 ;;
  esac
done

# --- noldorian CLIs ----------------------------------------------------
PY="$(command -v python3)"
echo "== installing: noldorian (unified family distribution, user site) =="
"$PY" -m pip install --user --quiet "noldorian>=0.2,<0.3" \
  && echo "  noldorian + keyabra + xadabra + xabra + binabra + xalakazam: ok" \
  || { echo "  noldorian: FAILED" >&2; exit 1; }

USER_BIN="$("$PY" -m site --user-base)/bin"
case ":$PATH:" in
  *":$USER_BIN:"*) ;;
  *) echo "== NOTE: add to PATH: export PATH=\"$USER_BIN:\$PATH\" ==" ;;
esac

# --- spellbook (optional) ---------------------------------------------
if [ "$WANT_SPELLS" = 1 ]; then
  if [ ! -d "$HOME/spells/.git" ]; then
    if ! command -v gh >/dev/null 2>&1 || ! gh auth status >/dev/null 2>&1; then
      echo "bootstrap: --spells requires authenticated gh (run 'gh auth login')" >&2
      exit 1
    fi
    echo "== cloning spellbook to ~/spells =="
    gh repo clone "$SPELLS_REPO" "$HOME/spells" -- --depth 1
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

  # --- spell-tongue font (P8, spells#3) -------------------------------
  # The spellbook clone above already carries the .otf, so installing it is a copy
  # into the OS font dir — no download, no CDN. This is the "renderer exists" half
  # of the distribution ladder: with the font present a surface draws the glyphs;
  # without it, tongue-render falls back to real-Unicode marks or the romanization.
  # Rendering is progressive enhancement, so EVERY failure here is a warning and
  # never a non-zero exit — a machine that cannot install a font still has a
  # completely working spellbook.
  FONT_SRC="$HOME/spells/fonts/SpellTongueTengwar.otf"
  FONT_MANIFEST="$HOME/spells/fonts/KIT.manifest.json"
  # A font is a parsed binary consumed by the OS text stack, so installing one
  # whose bytes nobody checked is not a cosmetic act. Verify against the kit
  # manifest (spells#2) before copying. Verification FAILING blocks the install;
  # verification being UNAVAILABLE (older spellbook with no manifest) does not —
  # that would break bootstrap on every clone predating the manifest.
  if [ -f "$FONT_SRC" ] && [ -f "$FONT_MANIFEST" ]; then
    if ! "$PY" - "$FONT_MANIFEST" "$FONT_SRC" <<'PYCHECK'
import hashlib, json, sys
manifest, font = sys.argv[1], sys.argv[2]
want = next((e["sha256"] for e in json.load(open(manifest))["files"]
             if e["path"].endswith("SpellTongueTengwar.otf")), None)
if not want:
    sys.exit(0)  # not pinned by this manifest — nothing to contradict
h = hashlib.sha256()
with open(font, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 16), b""):
        h.update(chunk)
got = h.hexdigest()
if got != want:
    print(f"   expected {want[:16]}… got {got[:16]}…")
    sys.exit(1)
PYCHECK
    then
      echo "== NOTE: spell-tongue font FAILED its manifest pin — not installing =="
      FONT_SRC=""
    fi
  fi
  if [ -n "$FONT_SRC" ] && [ -f "$FONT_SRC" ]; then
    case "$(uname -s)" in
      Darwin) FONT_DIR="$HOME/Library/Fonts" ;;
      *)      FONT_DIR="$HOME/.local/share/fonts" ;;
    esac
    if mkdir -p "$FONT_DIR" 2>/dev/null && cp "$FONT_SRC" "$FONT_DIR/" 2>/dev/null; then
      echo "== spell-tongue font installed to $FONT_DIR =="
      # Linux needs the fontconfig cache refreshed before apps see a new face;
      # macOS picks it up on its own. Missing fc-cache is fine — the file is there.
      if command -v fc-cache >/dev/null 2>&1; then
        fc-cache -f "$FONT_DIR" >/dev/null 2>&1 || true
      fi
    else
      echo "== NOTE: could not install spell-tongue font to $FONT_DIR (romanization still renders everywhere) =="
    fi
  fi
fi

echo
echo "== done. orient yourself: =="
echo "   $USER_BIN/xalakazam --deploy"
echo "   $USER_BIN/xalakazam --spells"
