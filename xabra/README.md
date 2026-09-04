# xabra — Noldorian operator CLI

Ships with `pip install noldorian`. Two jobs, one command:

**Vault** (paste-once, child env, nothing on argv):

```bash
xabra env init
xabra env set TOKEN_NAME
xabra run --env-file ~/.config/noldorian/vault.env -- ./deploy.sh
xabra pypi publish .
```

**Verified install** from *your* registry (default empty):

```bash
# ~/.config/noldorian/apps.json — operator-supplied sources
xabra --list
xabra --app NAME --install [--dmg PATH] [--yes]
xabra --doctor
```

The public package does not ship a baked application catalog. GitHub (`gh`)
is optional and only used if an operator registry entry says so.
