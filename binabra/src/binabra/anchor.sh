#!/usr/bin/env bash
# abra anchor — sets BIN to the directory of the script that sourced this file.
#
# Portable (pip):
#   source "$(abra sh)"
#   exec "$BIN/my-tool" "$@"
#
# Co-located (copy anchor.sh next to your scripts as "abra"):
#   source "$(dirname "${BASH_SOURCE[0]}")/abra"
#   exec "$BIN/my-tool" "$@"

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  _caller="${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}"
  BIN="$(cd "$(dirname "$_caller")" && pwd)"
  export BIN
  return 0 2>/dev/null || true
fi

echo "abra: source this file; do not execute directly" >&2
echo "  source \"\$(abra sh)\"" >&2
exit 1
