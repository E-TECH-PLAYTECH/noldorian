"""PyPI API helpers (stdlib only — no twine yank required)."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

PYPI_URL = "https://pypi.org"


def yank_release(package: str, version: str, token: str, reason: str) -> tuple[bool, str]:
    """Yank a release on PyPI via Warehouse API. Returns (ok, message)."""
    url = f"{PYPI_URL}/api/projects/{package}/{version}"
    body = json.dumps({"yanked": True, "yanked_reason": reason}).encode()
    auth = base64.b64encode(f"__token__:{token}".encode()).decode()
    req = urllib.request.Request(
        url,
        data=body,
        method="PATCH",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode().strip()
            if raw:
                try:
                    data = json.loads(raw)
                    yanked = data.get("yanked", True)
                    return True, f"yanked={yanked}"
                except json.JSONDecodeError:
                    pass
            return True, "yanked"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode().strip()
        try:
            parsed = json.loads(detail)
            detail = parsed.get("message") or parsed.get("error") or detail
        except json.JSONDecodeError:
            pass
        if len(detail) > 200:
            detail = detail[:200] + "..."
        return False, f"HTTP {exc.code}: {detail}"
