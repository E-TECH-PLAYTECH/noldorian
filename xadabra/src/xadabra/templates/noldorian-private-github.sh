#!/bin/zsh
# Noldorian private GitHub publish — run with: xadabra (clipboard) or xadabra this-file.sh
set -euo pipefail

ORG="{{ORG:GitHub org:Everplay-Tech}}"
REPO="{{REPO:Private repo name:noldorian}}"
TAG="{{TAG:Git tag:v0.1.1}}"
DEST="{{DEST|path:Monorepo folder (e.g. ~/Projects/noldorian)}}"
PROJECTS="{{PROJECTS|path:Projects parent (e.g. ~/Projects)}}"

echo "=== pack monorepo ==="
xadabra noldorian pack --dest "$DEST" --projects-dir "$PROJECTS" --org "$ORG" --repo "$REPO" --tag "$TAG" --force

echo ""
echo "=== push to GitHub (create empty private repo first in browser) ==="
xadabra noldorian push --dest "$DEST" --org "$ORG" --repo "$REPO" --tag "$TAG"

echo ""
echo "=== install lines ==="
xadabra noldorian install --org "$ORG" --repo "$REPO" --tag "$TAG"

echo ""
read "?Yank public PyPI versions? [y/N] " YANK
if [[ "$YANK" == [yY]* ]]; then
  xadabra noldorian yank
fi

echo "✅ done — https://github.com/$ORG/$REPO"
