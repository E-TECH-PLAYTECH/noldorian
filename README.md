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

Doctor works with no extra daemon. An optional Gondolin extension may expose a
Unix-socket capability broker; missing it is not a failure for everyday vault
use.

## Vault

```bash
xabra env init
xabra env set TOKEN_NAME
xabra run --env-file ~/.config/noldorian/vault.env -- your-command
# equivalent:
noldorian run --env-file ~/.config/noldorian/vault.env -- your-command
```

Vault lines: `NAME=value`, `NAME__FILE=/path` (contents at run time),
`NAME__CMD=cmd` (stdout at run time). The file must be mode 0600.

If `~/.config/noldorian/` has no vault yet, a 0.2.0-era file under
`~/.config/keyabra/` is still read.

Hidden PyPI upload (token never on argv):

```bash
xabra pypi publish .
```

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
