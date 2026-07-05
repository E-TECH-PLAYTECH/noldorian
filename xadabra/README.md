# xadabra

Proprietary — Copyright © 2026 Everplay-Tech LLC. See [LICENSE](LICENSE).

Paste-once runner for AI shell blocks. No more hand-editing `{{placeholders}}` in command blocks.

**Noldorian** tier (pip operator tools — not `snx` spells). Siblings: **binabra**, **keyabra**.

## Install

```bash
pip install xadabra
```

## Example

An AI gives you this block:

```bash
#!/bin/zsh
cd {{FOLDER|path:Where is the folder?}}
export API_KEY={{!API_KEY:Paste the API key}}
./deploy.sh
```

Copy it, then:

```bash
xadabra
```

`xadabra` reads your clipboard, prompts once per placeholder (API key hidden), shows a masked preview, asks `Run? [y/N]`, then executes via zsh.

## Placeholder syntax

| Form | Meaning |
|------|---------|
| `{{NAME}}` | Prompt `NAME:` |
| `{{NAME:Question}}` | Custom prompt |
| `{{NAME:Question:default}}` | Default if you press Enter |
| `{{!NAME:Question}}` | Secret (`getpass`, masked in preview) |
| `{{NAME\|path:Question}}` | Must be an existing path (`~`, quotes, `\\ ` unescaped) |

Each unique `NAME` is prompted once and substituted everywhere.

## Usage

```bash
xadabra              # read script from clipboard (pbpaste)
xadabra script.sh    # read from file
xadabra - <<'EOF'    # read from stdin
echo hello {{WHO:Who?}}
EOF

xadabra --dry-run    # preview only
xadabra --yes        # skip confirmation
```

## Safety

- No network, no telemetry
- Optional local history: `~/.xadabra/history.jsonl` (scripts only — **never** placeholder values)
- Secrets masked as `*****` in previews and history

## Publish

```bash
pip install binabra keyabra build twine
cd ~/Projects/xadabra && python3 -m build
keyabra pypi publish
```

## Tests

```bash
cd ~/Projects/xadabra
python3 -m unittest discover -s tests -v
```
