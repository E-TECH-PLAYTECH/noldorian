# binabra

Proprietary — Copyright © 2026 Everplay-Tech LLC. See [LICENSE](LICENSE).

Portable **bin directory anchor** for shell scripts. Install once, reuse the same header anywhere.

- **PyPI:** `binabra`
- **CLI:** `abra` (short invocation)
- **Tier:** Noldorian (pip operator tool — not an `snx` spell). See `~/spells/NOLDORIAN.md`

## Install

```bash
pip install binabra
```

Ensure pip's script dir is on PATH (macOS example):

```bash
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
```

## Use anywhere

At the top of any shell script:

```bash
source "$(abra sh)"
exec "$BIN/my-sibling-tool" "$@"
```

`BIN` becomes the directory **containing your script**.

## Bootstrap a project

```bash
abra init          # creates ./bin/abra
abra colocate bin  # copy abra into existing bin/
```

Co-located scripts:

```bash
source "$(dirname "${BASH_SOURCE[0]}")/abra"
exec "$BIN/other-script" "$@"
```

## CLI

| Command | Purpose |
|---------|---------|
| `abra sh` | Path to `anchor.sh` for sourcing |
| `abra embed` | Print `source "$(abra sh)"` |
| `abra dir` | Discover bin (`ABRA_BIN`, project `bin/`, `~/.local/bin`) |
| `abra exec tool args` | Run sibling from discovered bin |
| `abra init [dir]` | Create `bin/abra` in a project |
| `abra colocate [dest]` | Copy `abra` into a bin folder |

## Publish to PyPI

### 1. Create an API token

https://pypi.org/manage/account/token/

- Scope: **Entire account** (first time) or **Project: binabra** (after first upload)
- Copy the token (`pypi-...`)

### 2. Build

```bash
cd ~/Projects/binabra
python3 -m pip install --user build twine
python3 -m build
```

### 3. Upload

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR-TOKEN-HERE
twine upload dist/*
```

Or enter credentials when prompted:

```bash
twine upload dist/*
# username: __token__
# password: pypi-...
```

### 4. Verify

```bash
pip install binabra
abra --version
abra embed
```

PyPI project page: https://pypi.org/project/binabra/

## Python API

```python
from binabra import anchor_dir, sibling, discover_bin

anchor_dir(__file__)
sibling("run.sh", __file__)
discover_bin()
```
