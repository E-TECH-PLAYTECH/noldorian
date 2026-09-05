# Noldorian

Public, pip-installable operator tools. One package: `noldorian`.

Spells (`snx`) are a separate, optional local toolkit. Noldorian does not
require GitHub, a spellbook, or a privileged broker.

| CLI | Role |
|-----|------|
| `noldorian` | doctor + optional extension client |
| `xabra` | 0600 vault, `run --env-file`, verified install |
| `xadabra` | `{{placeholder}}` script runner |
| `xalakazam` | orienter / owner checkpoints |
| `abra` | bin-directory anchor |
| `noldorian-mcp` | stdio MCP |

Install: `python3 -m pip install noldorian` or `pipx install noldorian`.
Upgrade: `pipx upgrade noldorian` (or `noldorian upgrade --confirm`). The vault
file is not inside the install. Factory publish is Drive then twine, not GitHub.
