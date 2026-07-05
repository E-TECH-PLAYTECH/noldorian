# Claude Code Cloud — xadabra

## Policy

| In cloud | Allowed | Not allowed |
|----------|---------|-------------|
| Project repo | read/write, build, test | — |
| `~/spells` spellbook | **reference** (read docs, learn patterns) | **`snx` / spell casts** |
| Noldorian | `xadabra --cloud` with plain shell | clipboard `xadabra`, interactive prompts |

Spells are **MacBook Pro (head)** infrastructure — receipts, wards, fleet. The **mini**
is the powerhouse; the **Air** is the lens (`lookie`, `macmini`). Cloud agents use
**xadabra + shell** only. `xadabra --cloud` **rejects scripts containing `snx`**.

---

Add to your project's **CLAUDE.md**:

```markdown
## Cloud agent policy (Everplay)

You have the project repo and may read ~/spells for reference.
Do NOT cast spells in cloud sessions — no `snx`, no `python3 -m snax.cli`.

For shell work with secrets/paths:
1. Write `.xadabra/<task>.sh` with {{placeholders}} — plain bash only
2. Set XADABRA_<NAME> from secrets / containerEnv
3. Run: python3 -m xadabra --cloud -y .xadabra/<task>.sh

Install: pip install xadabra
Never: pip install -e ~/spells/snax in cloud (no snx on PATH)
```

---

## Example script (`.xadabra/ci-check.sh`)

```bash
cd {{REPO|path:Repo root}}
export API_KEY={{!API_KEY:API key}}
npm test
./scripts/deploy-staging.sh
```

## Example run

```bash
export XADABRA_REPO=/workspace/myapp
export XADABRA_API_KEY="$API_KEY"
python3 -m xadabra --cloud -y .xadabra/ci-check.sh
```

## devcontainer.json (recommended)

Clone spells for **read-only reference**; do not install snx:

```json
{
  "containerEnv": {
    "PIP_USER": "1",
    "PIP_BREAK_SYSTEM_PACKAGES": "1",
    "PYTHONUSERBASE": "/home/node/.claude/python-user",
    "XADABRA_CLOUD": "1"
  },
  "postCreateCommand": "pip install xadabra",
  "features": {},
  "customizations": {
    "vscode": {
      "settings": {}
    }
  }
}
```

Optional init (read-only spellbook mirror):

```bash
git clone --depth 1 git@github.com:Everplay-Tech/spells.git /opt/spells-ref
# do NOT: pip install -e /opt/spells-ref/snax
```

## Head Mac (operator)

When cloud work needs a spell (ios-ship, macmini job, fleet): stop and tell the operator
to run it on the **MacBook Pro (head)** or dispatch to the **mini** via head spells.

On the **Air (lens)**, use `lookie` / `macmini` to view and relay; xadabra with clipboard
for operator paste-runs.
