"""PyPI release status helpers (stdlib only).

PyPI does not expose a working programmatic yank API on production as of 2026:
- PATCH /api/projects/{name}/{version} — not deployed (warehouse PR #16912)
- POST upload.pypi.org/legacy/ :action=yank — returns 405

Yanking must be done in the web UI: Options → Yank on each release.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

PYPI_URL = "https://pypi.org"
DEFAULT_YANK_REASON = "Moved to private GitHub: https://github.com/Everplay-Tech/noldorian"


def release_yanked(package: str, version: str) -> bool | None:
    """Return yanked state, or None if the release is missing."""
    url = f"{PYPI_URL}/pypi/{package}/{version}/json"
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return bool(data.get("info", {}).get("yanked"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def manage_releases_url(package: str) -> str:
    return f"{PYPI_URL}/manage/project/{package}/releases/"


def yank_manual_steps(package: str, version: str, *, reason: str = DEFAULT_YANK_REASON) -> str:
    return (
        f"1. Open {manage_releases_url(package)}\n"
        f"2. Find version {version} → Options → Yank\n"
        f"3. Reason: {reason}"
    )
