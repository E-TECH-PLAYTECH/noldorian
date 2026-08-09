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

## Discord bot token → Google Secret Manager

Use this operator rite after Discord reveals a newly reset token:

```bash
keyabra discord gcp-store \
  --application-id 1532476149249216542 \
  --guild-id 1532387746604384306 \
  --project everplay-centaur-chess \
  --secret everplay-discord-agent-relay-token
```

The token is entered at a hidden prompt. Keyabra first verifies the bot identity
and intended guild against Discord. Only then does it send the token to
`gcloud secrets versions add` over stdin, read the latest version back, and
repeat the live Discord verification. The receipt contains identity, guild,
project, secret, and version metadata—never the token.

Do not scrape a token from portal DOM text. The operator should copy the value
shown by Discord and paste it directly into Keyabra's hidden prompt.

## Cursor User API key → Google Secret Manager

After creating a **User API Key** in the
[Cursor Cloud Agents dashboard](https://cursor.com/dashboard/cloud-agents):

```bash
keyabra cursor gcp-store \
  --project everplay-centaur-chess \
  --secret everplay-cursor-sdk-api-key
```

The key is entered at a hidden prompt. Keyabra validates it against Cursor's
official `GET /v0/me` identity endpoint, sends it to Google Secret Manager over
stdin, reads it back, and repeats the live validation. The receipt contains
only the Cursor key name, account identity, project, secret, and version
metadata—never the API key.

Use a Cursor **User API Key**, not an Admin API key or a model-provider BYOK
key from Cursor's Models settings.

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
- Provider-generated tokens are live-validated before and after durable storage

## Non-disclosing vault probe

Use the same fail-closed loader as `keyabra run` to verify that one logical
vault entry is present and resolves to a non-empty value without printing the
value:

```bash
keyabra env probe OPENAI_API_KEY \
  --file ~/.config/keyabra/everplay-release.env
```

The JSON receipt contains only the vault path, variable name, permission mode,
and boolean validation results. Direct entries, `NAME__FILE` pointers, and
`NAME__CMD` providers are validated through the customer runtime path. Unsafe
vault permissions, malformed entries, missing pointers, failed commands,
missing names, and empty resolved values fail closed.
