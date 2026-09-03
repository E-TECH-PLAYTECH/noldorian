# Noldorian — the PyPI / High-Elven tier

**Noldorian** is the portable, pip-installable boundary for human-gated
credentials and deterministic operator tooling. It sits in the [Rosetta
layer](README.md#the-doctrine--why-spells-save-tokens) beside spells.

| Tier | Invocation | Registry | Interactive? | Network? |
|------|------------|----------|--------------|----------|
| **Spell** | `snx <name>` | `snx list` / discovery | **No** — flags/env only | Usually local |
| **Snack** | `snx <name>` | discovery (`kind: snx`) | No | Read-only digest |
| **Incantation** | `snx incantu --kuru "..."` | Esperanto → spell | No | Routes locally |
| **Noldorian** | `noldorian` after `pip install` | PyPI | Human gate only where explicitly invoked | Optional |

**Spells are for agents.** Receipt-bearing, JSON out, no prompts, no judgment holes unless
a **Rite**. **Noldorian's agent surface is deliberately narrow**: agents can ask
the broker to begin a reviewed human enrollment, inspect non-secret metadata,
and invoke fixed operations. The bundled operator tools retain their prompts,
clipboard, installer, and orientation duties behind their operator-facing
commands.

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
| `keyabra` | `keyabra` | Compatibility operator surface; the broker and human enrollment implementation are bundled by `noldorian`. |
| `xadabra` | `xadabra` | Clipboard/stdin script runner with `{{placeholders}}`, bundled by `noldorian`. |
| `xabra` | `xabra` | Verified direct-distribution app installer, bundled by `noldorian`. |
| `xalakazam` | `xalakazam` | Operator orientation and deployment playbooks, bundled by `noldorian`. |

The family source remains organized in its subdirectories, but one `noldorian`
distribution now installs the complete family and its compatibility entrypoints.

---

## Deploy anywhere

- **Bootstrap (any bash + python3 + git):** `bootstrap.sh` at repo root — auth via `gh` or `GITHUB_TOKEN`, pip user-installs the CLIs, `--all` for every package, `--spells` also clones the spellbook + `snx` shim. Works in cloud containers (Claude Code web): pipe it through curl with a `GITHUB_TOKEN` — see `xalakazam --bootstrap`.
- **MCP:** `noldorian-mcp` — zero-dependency stdio server for broker status,
  reviewed human enrollment, enrollment status, capability metadata, and fixed
  operations.
- **Homebrew (macOS):** this repo doubles as a tap — `brew tap everplay-tech/noldorian https://github.com/Everplay-Tech/noldorian.git && brew install everplay-tech/noldorian/noldorian` (`Formula/noldorian.rb`; scaffold — pip/bootstrap is the proven path). No cask: these are CLIs, not app bundles.

---

## Overlap with existing spells

| Spell | Noldorian cousin | Difference |
|-------|------------------|------------|
| `secret-run` | `keyabra` | Spell: args on CLI, JSON receipt, agent-facing. Keyabra: interactive getpass, human-facing. |
| `runner-install` / `macos-install-app` | `xabra` | Spells: this Mac, spellbook receipts, DUD3Runner/dmg-specific. Xabra: portable pip install, family-wide registry, works wherever `gh` is authenticated. |
| `invoke` / `route` | — | Spells route *within* the registry; Noldorian does not replace them. |

---

## Licensing and publication boundary

The generic Noldorian implementation is open source under the
[Apache License 2.0](LICENSE). Public code includes the protocol, clients,
operator tools, broker implementation, fixed adapters, and installation logic.

Live credentials, capability grants, account identifiers, authorized-machine
policy, and customer configuration are local state and are never packaged.
Provider components with incompatible or restricted licenses remain outside
the public distribution until redistribution rights are recorded.

Public PyPI releases use Trusted Publishing with short-lived OIDC credentials;
long-lived upload tokens do not belong in repositories or release workflows.

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
