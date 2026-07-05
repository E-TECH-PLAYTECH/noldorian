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

---

## Naming

- **PyPI name:** coined `-abra` family or other collision-free roots (`binabra`, `keyabra`, `xadabra`)
- **CLI:** short (`abra`, `keyabra`, `xadabra`) — invocation stays terse
- **Esperanto** remains the spellbook's *incantation* grammar (`incantu`), not the PyPI namespace

Planned progression (operator tools, not spells):

| Package | CLI | Role |
|---------|-----|------|
| `binabra` | `abra` | Bin-directory anchor — `source "$(abra sh)"` |
| `keyabra` | `keyabra` | Secure token prompt → run command (PyPI upload, etc.) |
| `xadabra` | `xadabra` | Clipboard/stdin script runner with `{{placeholders}}` |

Source lives in this repo (`Everplay-Tech/noldorian`) — one subdirectory per package.

---

## Overlap with existing spells

| Spell | Noldorian cousin | Difference |
|-------|------------------|------------|
| `secret-run` | `keyabra` | Spell: args on CLI, JSON receipt, agent-facing. Keyabra: interactive getpass, human-facing. |
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

> Cast `snx <spell>` on the **MacBook Pro (head)** only. **Air** lenses the mini;
> **mini** runs powerhouse jobs. Cloud: read spellbook for reference; **xadabra --cloud**
> with plain shell — blocks `snx`.

See also: [lexicon.json](lexicon.json) (`noldorian`), [AGENTS.md](AGENTS.md).
