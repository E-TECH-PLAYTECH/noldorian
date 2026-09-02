# Noldorian — the PyPI / High-Elven tier

**Noldorian** packages are portable, pip-installable CLI libraries. They sit in the
[Rosetta layer](README.md#the-doctrine--why-spells-save-tokens) beside spells — same
*kind* of problem (deterministic tooling for humans and agents), different *contract*.

| Tier | Invocation | Registry | Interactive? | Network? |
|------|------------|----------|--------------|----------|
| **Spell** | `snx <name>` | `snx list` / discovery | **No** — flags/env only | Usually local |
| **Snack** | `snx <name>` | discovery (`kind: snx`) | No | Read-only digest |
| **Incantation** | `snx incantu --kuru "..."` | Esperanto → spell | No | Routes locally |
| **Noldorian** | `<cli>` after `pip install` | PyPI | **Yes** (when designed for it) | Optional |

**Spells are for agents.** Receipt-bearing, JSON out, no prompts, no judgment holes unless
a **Rite**. **Noldorian is for operators** — paste-once runners, token prompts, bin
anchors: human-in-the-loop glue that agents should not pretend to be spells.

Do **not** register Noldorian packages in `snx discovery`. Agents: cast `snx` for spells;
`pip install` Noldorian when the covenant or task calls for portable CLI libs.

For provider-generated credentials, the operator ceremony belongs in
**Keyabra**, not in browser DOM extraction or a non-interactive spell. A rite
must validate the credential against the provider before storage, pass it to
the vault over stdin or an in-process channel, read it back, and validate it
again before reporting success. Receipts contain identities and resource
pointers only—never credential material.

Credential enrollment does not create software rights. A provider SDK with an
evaluation, beta, proprietary, or otherwise restricted license stays
internal-evaluation-only until the applicable production and redistribution
rights plus dependency review are recorded. Keyabra may bank the credential;
that is not authorization to bundle the SDK into a customer product.

For agent reuse, a plaintext Keyabra env-vault is not a sufficient isolation
boundary. Agents query and invoke credentials through the root-owned
[credential capability broker](SECURE_CAPABILITY_BROKER.md). The broker exposes
providers, resource scopes, availability, and fixed operations—never values,
custody paths, arbitrary commands, or a generic secret export. Legacy vault
entries are agent-safe only after owner import into the broker and reviewed
retirement of the plaintext source.

---

## Naming

- **PyPI name:** coined `-abra` family or other collision-free roots (`binabra`, `keyabra`, `xadabra`)
- **CLI:** short (`abra`, `keyabra`, `xadabra`) — invocation stays terse
- **Esperanto** remains the spellbook's *incantation* grammar (`incantu`), not the PyPI namespace

Planned progression (operator tools, not spells):

| Package | CLI | Role |
|---------|-----|------|
| `binabra` | `abra` | Bin-directory anchor — `source "$(abra sh)"` |
| `keyabra` | `keyabra` | Secure token prompt → run command plus the 0.3 agent capability broker. Legacy env-vaults remain owner/operator surfaces; agents use broker metadata and fixed operations. |
| `xadabra` | `xadabra` | Clipboard/stdin script runner with `{{placeholders}}` |
| `xabra` | `xabra` | Everplay app fetcher — `--app <name> --install/--update/--open` for direct-distribution (non-App-Store) apps; Gatekeeper-verified installs, JSON receipts at `~/.local/state/xabra/receipts/` |
| `xalakazam` | `xalakazam` | **The orienter — callable memory.** `--deploy` / `--spells` print the embedded playbooks for installing + strategically using Noldorian and the snx spellbook on any machine; `--bootstrap` prints the one-liners |

Source lives in `~/Projects/<name>/`, published separately from this repo.

---

## Deploy anywhere

- **Bootstrap (any bash + python3 + git):** `bootstrap.sh` at repo root — auth via `gh` or `GITHUB_TOKEN`, pip user-installs the CLIs, `--all` for every package, `--spells` also clones the spellbook + `snx` shim. Works in cloud containers (Claude Code web): pipe it through curl with a `GITHUB_TOKEN` — see `xalakazam --bootstrap`.
- **MCP:** `mcp/noldorian_mcp.py` — zero-dependency stdio server (tools: `orient`, `install_noldorian`, `install_spells`, `doctor`); register with `claude mcp add noldorian -- python3 …/mcp/noldorian_mcp.py` and any MCP-capable agent can self-serve the playbooks and installs.
- **Homebrew (macOS):** this repo doubles as a tap — `brew tap everplay-tech/noldorian https://github.com/Everplay-Tech/noldorian.git && brew install everplay-tech/noldorian/noldorian` (`Formula/noldorian.rb`; scaffold — pip/bootstrap is the proven path). No cask: these are CLIs, not app bundles.

---

## Overlap with existing spells

| Spell | Noldorian cousin | Difference |
|-------|------------------|------------|
| `secret-run` | `keyabra` | Spell: args on CLI, JSON receipt, agent-facing. Keyabra: interactive getpass, human-facing. |
| `runner-install` / `macos-install-app` | `xabra` | Spells: this Mac, spellbook receipts, DUD3Runner/dmg-specific. Xabra: portable pip install, family-wide registry, works wherever `gh` is authenticated. |
| `invoke` / `route` | — | Spells route *within* the registry; Noldorian does not replace them. |

---

## Licensing & gatekeeping

Noldorian packages are **proprietary** — Copyright © 2026 Everplay-Tech LLC. Same
stance as this spellbook ([LICENSE](LICENSE)).

PyPI.org is a **public index** — `pip install` still works for anyone, but
**legal use requires permission**. Proprietary on PyPI is notice, not a download gate.

**True gatekeeping** (when needed): private index (Gemfury, CodeArtifact, devpi) or
`pip install git+ssh://...` from private repos — do not rely on PyPI alone.

**Upload tokens:** scope per project at https://pypi.org/manage/account/token/

---

## Agent covenant (one line)

> Cast `snx <spell>` on the **MacBook Pro (head)** freely. **Air** lenses the mini;
> **mini** runs powerhouse jobs. **Cloud** (revised 2026-07-09): bootstrap `--spells`
> and cast freely — the spell is ephemeral, the RECEIPT is the product — but the
> **export ritual is mandatory before exit**: ship `~/spells/receipts/` + the new
> `akashic/events.jsonl` diff home in the PR (`receipts/<branch>/snax/`) and/or POST
> to the INNERTUBE; the head machine harvests them into the durable ledger on merge
> (`snx akashic-harvest <export-path> --confirm` — chain-sealed, provenance-tagged,
> idempotent). An unexported cast never happened.

See also: [lexicon.json](lexicon.json) (`noldorian`), [AGENTS.md](AGENTS.md).
