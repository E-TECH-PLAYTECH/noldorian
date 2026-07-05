"""PyPI API helpers (stdlib only — no twine yank required)."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request

PYPI_URL = "https://pypi.org"


def yank_release(package: str, version: str, token: str, reason: str) -> tuple[bool, str]:
    """Yank a release on PyPI. Returns (ok, message)."""
    url = f"{PYPI_URL}/pypi/{package}/{version}/yank/"
    data = urllib.parse.urlencode({"reason": reason}).encode()
    auth = base64.b64encode(f"__token__:{token}".encode()).decode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode().strip()
            return True, body or "yanked"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode().strip()
        try:
            detail = json.loads(detail).get("message", detail)
        except json.JSONDecodeError:
            pass
        return False, f"HTTP {exc.code}: {detail}"
