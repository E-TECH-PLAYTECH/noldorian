# xabra — Everplay-Tech app fetcher (Noldorian tier)

Install, update, and open **Everplay-Tech direct-distribution apps** — the ones
that don't come from the App Store (DUD3Runner, TULKAS, Knot, FX Lab, …).
Portable and pip-installable so any operator or agent, on any machine with an
authenticated `gh`, gets the same receipt-bearing install path.

```bash
pip install "git+https://github.com/E-TECH-PLAYTECH/noldorian.git#subdirectory=xabra"
```

## Usage — one action per invocation

```bash
xabra --list                                # known apps + what's installed
xabra --app dud3runner --status             # installed vs latest available
xabra --app dud3runner --install [--yes]    # fetch → Gatekeeper/codesign verify → /Applications
xabra --app dud3runner --update             # install only if newer resolves
xabra --update --all --yes                  # sweep every known app
xabra --app dud3runner --open
xabra --app dud3runner --update --protocol  # repoint MCP enrollment at the installed binary
xabra --doctor                              # gh auth + macOS tool check
```

Apps that embed an MCP protocol binary (dud3runner → `dude-mcp`) declare it in
their spec; `--status` then reports enrollment **drift** (agent sessions running
a different binary than the installed app). `--update --protocol` converges,
idempotently, on the steady state:

```
~/.claude.json enrollment → ~/.local/bin/<mcp_name> shim → installed app's binary
```

The shim path never changes, so once converged, **app updates propagate to
agents automatically** — no re-enrollment, no manual refresh. `--install` /
`--update` of a protocol-bearing app re-converges as part of the install.
Re-running is always safe ("already converged" is a no-op). `~/.claude.json`
edits bank a backup first. Running sessions keep the server they spawned;
each new session picks up the current binary through the shim.

Add `--json` to anything for a machine-readable receipt. Mutating actions
always bank a receipt at `~/.local/state/xabra/receipts/` and back up the
replaced app to `~/.local/state/xabra/backups/` — receipts over claims.

`--dmg PATH` installs from a local dmg/tar.gz when no release/artifact has
been published yet (e.g. a fresh `macos-notarize` cast).

## App registry

Built-in registry covers the family; extend or override per-machine at
`~/.config/xabra/apps.json` (same schema, `null` deletes an entry):

```json
{
  "myapp": {
    "kind": "app",
    "app": "MyApp.app",
    "repo": "Everplay-Tech/myapp",
    "sources": [
      { "type": "release",  "repo": "Everplay-Tech/myapp", "asset": "*.dmg" },
      { "type": "artifact", "repo": "Everplay-Tech/myapp", "pattern": "MyApp-build-*" },
      { "type": "local",    "path": "~/myapp/build/MyApp.dmg" }
    ]
  }
}
```

Sources resolve in order: GitHub release asset → newest Actions artifact →
local path. `kind: "cli"` installs a `tar.gz` binary to `~/.local/bin` instead.

## Boundaries

- **Verification is non-negotiable**: `.app` installs must pass `spctl --assess`
  and `codesign --verify --deep --strict` before anything touches /Applications.
- Non-interactive sessions must pass `--yes` — xabra never self-confirms.
- Spell cousin: `snx runner-install` (DUD3Runner-specific, spellbook receipts).
  xabra is the portable, family-wide Noldorian; it does not require the spellbook.

Licensed under the [Apache License 2.0](LICENSE).
