"""xalakazam — Noldorian orienter. Callable memory for any machine.

`xalakazam --deploy` prints how to install and use Noldorian. The docs are
embedded — the command works wherever the package is pip-installed.
"""

from __future__ import annotations

__version__ = "0.2.3"

DEPLOY = """\
# XALAKAZAM --deploy — Noldorian: what it is, how to install it, how to use it

## What Noldorian is (30 seconds)

Noldorian keeps API tokens out of chat, argv, and logs. A human pastes a
secret once into a 0600 vault. A child process gets the environment and does
the work. Agents discover the install and the vault *contract*; they never
receive secret values.

Install one public package:

    python3 -m pip install noldorian

| CLI | Use it for |
|-----|------------|
| `noldorian` | doctor, optional Gondolin extension client |
| `xabra` | vault (`run --env-file`, env, copy) and verified install |
| `xadabra` | clipboard/stdin script runner with {{placeholders}} |
| `xalakazam` | this orienter |
| `abra` | bin-directory anchor: `source "$(abra sh)"` |
| `noldorian-mcp` | stdio MCP (doctor, orient, names-only vault, optional extension) |

## Vault

The first `noldorian` or `xabra` command (including `noldorian doctor`)
creates `~/.config/noldorian/` (0700) and an empty `vault.env` (0600).
Agents must not mkdir that directory. Then the owner fills names:

    xabra env set TOKEN_NAME

Every consumer thereafter:

    xabra run --env-file ~/.config/noldorian/vault.env -- <cmd>

(also `noldorian run --env-file ... -- <cmd>`). Vaults hold ids and pointers
(`NAME__FILE=/path`, `NAME__CMD=cmd`) so key material is not duplicated.
The file must be 0600 or Noldorian refuses. A leftover file at
`~/.config/keyabra/keyabra.env` is not the live vault. If it still exists,
Noldorian will not create an empty canonical vault on top of it.

## Agents

Point MCP at `noldorian-mcp` from the pip install. Call `doctor` first.
`list_vault_names` returns names only. `child_run_template` returns the
owner-run command. Never paste secrets into chat.

An optional Gondolin extension may expose a Unix-socket capability broker.
Everyday vault use does not require it. `noldorian doctor` reports
extension absent without failing.

## PATH

After `pip install --user`, add the user script dir to PATH
(`python3 -m site --user-base` + /bin). Verify: `noldorian doctor`.
"""

SPELLS = """\
# XALAKAZAM --spells

Noldorian does not install a spellbook. If this machine already has `snx`,
use it. Do not clone private repositories or set GITHUB_TOKEN to install
Noldorian — `python3 -m pip install noldorian` is the install path.
"""

BOOTSTRAP_HINT = """\
# Quick install

python3 -m pip install noldorian
# or
uv tool install noldorian

Then: noldorian doctor
"""

OWNER_ACTIONS = """\
# XALAKAZAM --owner-actions — Noldorian owner checkpoint rite

## Purpose

Use this rite when an agent reaches a step that only the owner can perform:
open an app, tap or approve, pair or unlock a device, authenticate a client,
confirm a purchase, or change a host permission. The agent sends one precise
message and waits. Silence, a cable, a stale UI, or a prior permission choice
is not completion.

## Operator protocol

1. Do one bounded owner action at a time. Name the exact app, screen, and gate.
2. Never paste a passcode, token, API key, password, auth header, or private
   screenshot into chat. For credentials, use `xabra`'s hidden prompt
   (`xabra env set` / `xabra run --env`); report only identity and outcome.
3. Treat "I can purchase" as capability, not authorization. The owner must
   explicitly confirm `purchase <product>` before a payment flow starts and
   performs the final confirmation themselves.
4. If the agent reports Full access but the runtime is restricted, do not fake
   it with an environment variable or a local write probe. Change the supported
   host permission setting, then re-read the runtime state once.
5. After the owner replies with the requested non-secret phrase, make one fresh
   supported verification. Continue only when the state actually changed.

## Message template

OWNER CHECKPOINT
Need: <one owner action>
Where: <exact app, device, or host surface>
Why: <the gate this changes>
Do: <one to three short steps>
Do not send: passcodes, tokens, API keys, passwords, or private screenshots
Reply: "<exact completion phrase>"
After that: one fresh verification, then continue.
Until then: no repeated probe, reinstall, deletion, or alternate-client loop.

## Receipt shape

{"schema":"noldorian.owner-action-checkpoint/v1",
 "state":"owner_action_required|awaiting_confirmation|ready_to_verify|verified|held",
 "need":"one precise owner action", "surface":"app/device/host",
 "reply_phrase":"exact non-secret response",
 "next_verification":"one supported read",
 "secret_boundary":"secret material never enters chat, argv, logs, or receipt"}

Noldorian provides the operator ceremony; it does not grant host permissions,
click a financial confirmation, or bypass trust and authentication controls.
"""
