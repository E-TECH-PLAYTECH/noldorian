# binabra

Licensed under the [Apache License 2.0](LICENSE).

Portable **bin directory anchor** for shell scripts. Install once, reuse the same header anywhere.

Ships inside the unified public package (`abra` CLI).

## Install

```bash
python3 -m pip install noldorian
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

`abra` ships inside `python3 -m pip install noldorian`. It is not a separate PyPI project.

## Python API

```python
from binabra import anchor_dir, sibling, discover_bin

anchor_dir(__file__)
sibling("run.sh", __file__)
discover_bin()
```
