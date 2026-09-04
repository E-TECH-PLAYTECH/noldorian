# Noldorian

Noldorian keeps API tokens out of chat, argv, and logs. A human pastes a
secret once into a 0600 vault. A child process gets the environment and does
the work. Agents can discover the install and the vault contract; they never
receive secret values.

One public package. The CLIs `xabra`, `xadabra`, `xalakazam`, and `abra`
ship with it.

## Install

```bash
python3 -m pip install noldorian
# or
uv tool install noldorian
```

Then:

```bash
noldorian doctor
```

The first `noldorian` or `xabra` command creates `~/.config/noldorian/` (0700)
and an empty `vault.env` (0600). Agents must not mkdir that directory. Fill
names later with `xabra env set NAME` (hidden prompt). Values never print.

Doctor works with no extra daemon. An optional Gondolin extension may expose a
Unix-socket capability broker; missing it is not a failure for everyday vault
use.

## Vault

```bash
xabra env set TOKEN_NAME
xabra run --env-file ~/.config/noldorian/vault.env -- your-command
# equivalent:
noldorian run --env-file ~/.config/noldorian/vault.env -- your-command
```

Vault lines: `NAME=value`, `NAME__FILE=/path` (contents at run time),
`NAME__CMD=cmd` (stdout at run time). The file must be mode 0600.

A leftover `~/.config/keyabra/keyabra.env` is not the live Noldorian vault.
If that file still exists, `noldorian doctor` refuses to create an empty
canonical vault on top of it. Backup and remove the leftover, then rerun
`noldorian doctor` so the package can create `~/.config/noldorian` itself.

## Other CLIs

| CLI | Purpose |
|-----|---------|
| `xadabra` | Paste-once runner for scripts with `{{placeholders}}` |
| `xalakazam` | Orienter / doctor playbooks / owner checkpoints |
| `abra` | Portable bin-directory anchor |
| `xabra --list` | Verified install from **your** `~/.config/noldorian/apps.json` (empty by default) |

## MCP

```bash
noldorian-mcp
# equivalent: python3 -m noldorian.mcp
```

Always-on tools: `doctor`, `orient`, `list_vault_names` (names only),
`child_run_template`. Optional Gondolin tools are present when a socket exists;
they never return credential values.

## Python

```python
from noldorian.vault import load_env_file, run_with_env
from noldorian.client import BrokerClient  # optional extension
```

## License

Apache License 2.0. Report security issues privately to the maintainers; do
not open a public issue that contains secrets.
