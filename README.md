# Noldorian

Proprietary operator CLIs (Everplay-Tech LLC). **Not spells** — not in `snx` discovery.

| Package | CLI | Install |
|---------|-----|---------|
| binabra | `abra` | Bin-directory anchor |
| keyabra | `keyabra` | Secure token prompt → run command |
| xadabra | `xadabra` | Paste-once `{{placeholders}}` runner |

See [NOLDORIAN.md](NOLDORIAN.md) for taxonomy vs the spellbook.

## Install (private)

```bash
pip install "git+https://github.com/Everplay-Tech/noldorian.git#subdirectory=binabra"
pip install "git+https://github.com/Everplay-Tech/noldorian.git#subdirectory=keyabra"
pip install "git+https://github.com/Everplay-Tech/noldorian.git#subdirectory=xadabra"
```

SSH:

```bash
pip install "git+ssh://git@github.com/Everplay-Tech/noldorian.git#subdirectory=xadabra"
```

## Publish to PyPI (maintainers)

```bash
cd xadabra && keyabra pypi publish
```

## Cloud (Claude Code)

`xadabra --cloud` only — no `snx`. See `xadabra/integrations/CLAUDE-CLOUD.md`.
