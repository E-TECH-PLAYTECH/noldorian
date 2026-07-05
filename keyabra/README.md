# keyabra

Proprietary — Copyright © 2026 Everplay-Tech LLC. See [LICENSE](LICENSE).

Prompt for API tokens **once**, run the command — no export/copy/delete/notepad loop.

**Noldorian** tier (pip operator tools — not `snx` spells). Sibling: **binabra** (`abra`).

## Install

```bash
pip install keyabra
```

If `keyabra` is not found, pip may have installed it outside your PATH. Either:

```bash
# macOS — add pip's script dir (once, in ~/.zshrc)
export PATH="$HOME/Library/Python/3.9/bin:$HOME/.local/bin:$PATH"
```

Or run without PATH setup:

```bash
python3 -m keyabra pypi publish
```

Also need `twine` and `build` for PyPI uploads:

```bash
pip install build twine
```

## Publish binabra (or any project)

```bash
cd ~/Projects/binabra
keyabra pypi publish
```

That will:
1. Run `python -m build` if `dist/` is empty
2. Prompt: `PyPI token (pypi-...):` (hidden input)
3. Run `twine upload` — token never hits disk or your shell history

## Other commands

```bash
keyabra pypi upload dist/*
keyabra pypi publish ~/Projects/binabra --skip-build

# Generic — any secret env var + any command
keyabra run --env GITHUB_TOKEN -- gh auth status
keyabra run --env TWINE_PASSWORD --env TWINE_USERNAME -- twine upload dist/*
```

## Publish keyabra itself

First upload needs an account-scoped PyPI token: https://pypi.org/manage/account/token/

```bash
cd ~/Projects/keyabra
python3 -m pip install --user build twine
python3 -m build
keyabra pypi publish --skip-build   # after build, uses prompted token
```

## Security

- Uses `getpass` — token is not echoed
- Token lives only in process memory for the subprocess
- Never written to files or shell history
