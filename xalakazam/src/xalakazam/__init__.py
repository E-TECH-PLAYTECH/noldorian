"""xalakazam — the Everplay orienter. Callable memory, any machine, any session.

`xalakazam --deploy` and `xalakazam --spells` print the two playbooks below,
so an agent or human landing on a fresh machine (or a cloud container) knows
how to install and STRATEGICALLY use Noldorian and the snx spellbook without
any prior context. The docs are embedded — the command works wherever the
package is pip-installed, no repo checkout required.
"""

from __future__ import annotations

__version__ = "0.1.3"

DEPLOY = """\
# XALAKAZAM --deploy — Noldorian: what it is, how to install it, how to use it

## What Noldorian is (30 seconds)

Noldorian is Everplay-Tech's OPERATOR tier: portable, pip-installable CLIs for
humans and agents. It sits beside the snx spellbook (see `xalakazam --spells`):
spells are agent-facing (JSON receipts, no prompts, banked to a ledger);
Noldorian tools are the human-in-the-loop and cross-machine glue.
Source of truth: the PRIVATE repo github.com/Everplay-Tech/noldorian.

| CLI        | Package  | Use it for |
|------------|----------|------------|
| `keyabra`  | keyabra  | Secrets: getpass prompts AND 0600 env-vaults with run-time
|            |          | indirection (`NAME__FILE=/path`, `NAME__CMD=cmd`). Load with
|            |          | `keyabra run --env-file <vault> -- <cmd>` — secrets stay
|            |          | in-process, never argv, never duplicated to disk. |
| `xalakazam`| xalakazam| This orienter. `--deploy`, `--spells`, `--bootstrap`. |
| `xadabra`  | xadabra  | Clipboard/stdin script runner with {{placeholders}}.
|            |          | `xadabra --cloud` = plain-shell mode for cloud containers. |
| `abra`     | binabra  | Bin-directory anchor: `source "$(abra sh)"`. |
| `xabra`    | xabra    | Everplay app fetcher for direct-distribution apps
|            |          | (Gatekeeper-verified installs, receipts, MCP protocol shim). |

## Installing (pick the line that matches where you are)

Auth first: you need EITHER an authenticated `gh` CLI OR a GITHUB_TOKEN env var
with repo read on Everplay-Tech (repos are private).

1) Any machine with gh (macOS or Linux) — the bootstrap does everything:
   bash <(gh api -H "Accept: application/vnd.github.raw" \\
         repos/Everplay-Tech/noldorian/contents/bootstrap.sh)

2) Cloud container / Claude Code on the web (bash + GITHUB_TOKEN):
   curl -fsSL -H "Authorization: Bearer $GITHUB_TOKEN" \\
     -H "Accept: application/vnd.github.raw" \\
     https://api.github.com/repos/Everplay-Tech/noldorian/contents/bootstrap.sh \\
     | bash -s -- --all
   (No Homebrew needed there; containers are Linux, pip is lighter and works.)

3) Direct pip, one package at a time (TOKEN or gh credential helper):
   python3 -m pip install --user \\
     "git+https://github.com/Everplay-Tech/noldorian.git#subdirectory=keyabra"
   (swap subdirectory= for xalakazam / xadabra / binabra / xabra)

4) macOS Homebrew (the repo doubles as a tap — no cask; these are CLIs):
   brew tap everplay-tech/noldorian https://github.com/Everplay-Tech/noldorian.git
   brew install everplay-tech/noldorian/noldorian

After install make sure the pip user bin dir is on PATH
(`python3 -m site --user-base` + /bin — e.g. ~/Library/Python/3.9/bin or
~/.local/bin). Verify: `keyabra --version && xalakazam --spells | head -3`.

## Strategic use (the doctrine)

- SECRETS: never on argv, never pasted into chats. Owner provisions a vault
  once (`keyabra env init/set/set-file`); every consumer thereafter is
  `keyabra run --env-file <vault> -- <cmd>`. Vaults hold ids + POINTERS
  (`__FILE`, `__CMD`) so key material is never duplicated. Canonical Everplay
  release vault: ~/.config/keyabra/everplay-release.env (ASC App-Manager key
  id+p8 pointer, notary key, ORG_PAT__CMD=gh auth token).
- AGENT vs OWNER: agents must not self-authorize secret writes — permission
  classifiers/wards will (correctly) block them. The owner runs the granting
  command once (a settings permission rule, or the keyabra vault); agents
  consume forever after. Design flows around that split.
- CLOUD: cloud containers have NO spellbook and NO wards. Use plain shell +
  `xadabra --cloud`; report results back over HTTP (innertube) — a cloud
  "receipt" that lands nowhere is a claim, not a receipt.
- APPS: desktop family apps (e.g. DUD3Runner) install/update via `xabra`
  (Gatekeeper-verified, receipts, keeps MCP enrollments pointed at the
  installed binary).

## MCP

The repo ships an MCP server (mcp/noldorian_mcp.py) exposing orient /
install_noldorian / install_spells / doctor — register it and any MCP-capable
agent can self-serve this whole page and the installs:
  claude mcp add noldorian -- python3 /path/to/noldorian/mcp/noldorian_mcp.py
"""

SPELLS = """\
# XALAKAZAM --spells — the snx spellbook: install it, then live by receipts

## What spells are (30 seconds)

The spellbook (PRIVATE repo github.com/Everplay-Tech/spells) is a Python CLI
(`snx <spell> [args]`) where every cast returns a JSON RECEIPT and is banked to
an append-only ledger (the akashic/grimoire). Doctrine: **receipts over
claims** — report what the receipt says; never re-narrate raw shell output.
Spells are agent-facing: no prompts, flags/env only, mutating spells PREVIEW by
default and only `--confirm` writes (with timestamped backups).

## Installing on a new machine

Needs: python3, git, authenticated `gh` (repos are private).
  gh repo clone Everplay-Tech/spells ~/spells
  mkdir -p ~/bin && cat > ~/bin/snx <<'SH'
#!/bin/bash
# snx — global wrapper for the Snax CLI
exec /usr/bin/env PYTHONPATH="$HOME/spells/snax:${PYTHONPATH}" python3 -m snax.cli "$@"
SH
  chmod +x ~/bin/snx   # ensure ~/bin is on PATH
Verify: `snx list | head` and `snx snx-repo spells`.
NOTE: cloud containers deliberately do NOT get the spellbook (no wards there,
so no receipts ledger) — in the cloud use plain shell / `xadabra --cloud`.

## Strategy (how to actually work)

1. ROUTE FIRST: before raw shell, `snx route "<task>"` ranks spells for the
   job; `snx list` shows the whole book. If a spell exists, cast it.
2. THE BIG DEFAULTS:
   - repo state: `snx snx-repo <repo>` (never hand-assembled git)
   - commit: `snx commit-files <repo> "<msg>" <named files>` — NEVER `git add -A`
   - push: `snx git-push <repo> [remote] [branch] --confirm` (previews first)
   - checkout/branch: `snx git-co` · tags: `snx git-tag` · PRs: `snx gh-pr`
     (create/checks/watch/view + a GUARDED merge that refuses unless the FULL
     check set is green)
   - CI runs: `snx gh-run list|jobs|logs|watch`
   - long jobs (archives, notarization): dispatch DETACHED via
     `snx conjure <spell> ...` then scry `conjure --wait <job> --timeout 165`
     — direct calls die at tool timeouts; never poll-loop.
3. WARDS ARE THE FLOOR: DALEK hooks block `git add -A`, secret exfiltration,
   vault writes. If a ward nudges you toward a spell, heed it. Break-glass
   exists (`snx ward`) but only the OWNER may cast it.
4. MINT ON REPETITION: when a raw shell shape recurs (the mintward tally flags
   it), mint a spell: `snx mint <name> --like <nearest-donor>`, fill the body,
   smoke it, commit. The book is self-improving; leave it richer than you
   found it.
5. IDENTITY: before committing in any Everplay repo, repo-local
   user.email = 240267972+Everplay-Tech@users.noreply.github.com
   (GitHub blocks pushes exposing the private address). If unpushed commits
   carry the private email: `snx git-reauthor <repo> --base origin/<branch>`.
6. RELEASE PIPELINES (iOS family): every app ships by ONE dispatch —
   `gh workflow run release.yml -f distribute=true`. Dry-run first via a
   `release-dry-run/**` branch push (archive+sign+verify, no upload). Never
   `gh run rerun` a bump-pushing workflow (tag guard fires) — fresh-dispatch.
   Cloud signing needs the App-Manager ASC key; "Cloud signing permission
   error" = wrong key, swap don't debug.

## One-liner mental model

> route → cast → read the receipt → (repeat) → mint what recurs.
"""

BOOTSTRAP_HINT = """\
# Quick bootstrap (copy-paste)

# with gh:
bash <(gh api -H "Accept: application/vnd.github.raw" repos/Everplay-Tech/noldorian/contents/bootstrap.sh) --all

# with GITHUB_TOKEN only (cloud / Claude Code web):
curl -fsSL -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github.raw" \\
  https://api.github.com/repos/Everplay-Tech/noldorian/contents/bootstrap.sh | bash -s -- --all
"""
