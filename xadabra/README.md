# xadabra

Licensed under the [Apache License 2.0](LICENSE).

Paste-once runner for AI shell blocks. No more hand-editing `{{placeholders}}` in command blocks.

**Noldorian** tier (pip operator tools — not `snx` spells). Ships inside `pip install noldorian`.

## Install

```bash
python3 -m pip install noldorian
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

## Legacy Noldorian source workflow (`xadabra noldorian`)

The normal installation is the unified public package, which includes all
family CLIs and the agent-safe MCP server:

```bash
python3 -m pip install noldorian==0.2.0
```

The commands below are maintainer-only compatibility helpers for packing or
publishing source. They are not the agent enrollment path:

```bash
xadabra noldorian guide          # checklist (browser steps + commands)
xadabra noldorian pack           # refresh ~/noldorian subdirs
xadabra noldorian push           # git commit, tag, push (prompts org/repo)
xadabra noldorian install        # pinned unified install command
xadabra noldorian yank           # legacy PyPI maintenance (token prompt)

# Or paste-once full flow (copy template → xadabra):
xadabra noldorian script --copy  # clipboard
xadabra                          # prompts ORG/REPO/paths, preview, run
```

Template path (for `xadabra path/to/template.sh`):

```bash
xadabra noldorian script --path
```

## Safety

- No network, no telemetry
- Optional local history: `~/.xadabra/history.jsonl` (scripts only — **never** placeholder values)
- Secrets masked as `*****` in previews and history

## Tests

```bash
cd ~/noldorian/xadabra
python3 -m unittest discover -s tests -v
```
