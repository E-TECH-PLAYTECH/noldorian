"""Validate a Cursor User API key and store it in Google Secret Manager.

The key is accepted by the caller through an in-process hidden prompt, sent to
Cursor in an HTTP header, and sent to gcloud over stdin. It is never placed on
argv, written to a temporary file, or included in a receipt.
"""

from __future__ import annotations

import hmac
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from typing import Any, Callable


CURSOR_API_KEY_INFO_URL = "https://api.cursor.com/v0/me"


class CursorApiKeyError(RuntimeError):
    """A candidate key failed Cursor identity validation."""


class SecretStoreError(RuntimeError):
    """Google Secret Manager could not store or return the key."""


def validate_cursor_api_key(
    api_key: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, str]:
    """Require a live Cursor User API key and return non-secret identity."""
    candidate = api_key.strip()
    if not candidate:
        raise CursorApiKeyError("Cursor API key is empty")

    request = urllib.request.Request(
        CURSOR_API_KEY_INFO_URL,
        headers={
            "Authorization": f"Bearer {candidate}",
            "User-Agent": "keyabra-cursor-api-key-rite/1",
        },
    )
    try:
        with opener(request, timeout=20) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise CursorApiKeyError(
                    f"Cursor rejected the API key with HTTP {status}"
                )
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise CursorApiKeyError(
            f"Cursor rejected the API key with HTTP {exc.code}"
        ) from None
    except urllib.error.URLError as exc:
        raise CursorApiKeyError(
            f"Cursor could not be reached while validating the API key: {exc.reason}"
        ) from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise CursorApiKeyError(
            "Cursor returned an unreadable API-key response"
        ) from None

    if not isinstance(payload, dict):
        raise CursorApiKeyError("Cursor returned an invalid API-key response")
    api_key_name = str(payload.get("apiKeyName", "")).strip()
    if not api_key_name:
        raise CursorApiKeyError(
            "credential is not a recognized Cursor User API key"
        )
    return {
        "api_key_name": api_key_name,
        "user_email": str(payload.get("userEmail", "")).strip(),
        "created_at": str(payload.get("createdAt", "")).strip(),
    }


def _run_gcloud(
    args: list[str],
    *,
    stdin: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    executable = shutil.which("gcloud")
    if not executable:
        raise SecretStoreError(
            "gcloud is not installed or is not on PATH; install/authenticate it first"
        )
    try:
        return subprocess.run(
            [executable, *args],
            input=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        raise SecretStoreError("gcloud timed out") from None


def _require_gcloud_success(
    result: subprocess.CompletedProcess[bytes],
    action: str,
) -> bytes:
    if result.returncode == 0:
        return result.stdout
    detail = result.stderr.decode("utf-8", errors="replace").strip()[:300]
    suffix = f": {detail}" if detail else ""
    raise SecretStoreError(f"gcloud could not {action}{suffix}")


def store_cursor_api_key_in_gcp(
    api_key: str,
    *,
    project: str,
    secret: str,
    validator: Callable[..., dict[str, str]] = validate_cursor_api_key,
    gcloud: Callable[..., subprocess.CompletedProcess[bytes]] = _run_gcloud,
) -> dict[str, str]:
    """Validate, store via stdin, read back, and validate again."""
    candidate = api_key.strip()
    preflight = validator(candidate)

    describe = gcloud(
        [
            "secrets",
            "describe",
            secret,
            f"--project={project}",
            "--format=json",
        ]
    )
    if describe.returncode != 0:
        created = gcloud(
            [
                "secrets",
                "create",
                secret,
                f"--project={project}",
                "--replication-policy=automatic",
                "--format=json",
            ]
        )
        _require_gcloud_success(created, f"create secret {secret}")

    added = gcloud(
        [
            "secrets",
            "versions",
            "add",
            secret,
            f"--project={project}",
            "--data-file=-",
            "--format=json",
        ],
        stdin=candidate.encode("utf-8"),
    )
    version_payload = _require_gcloud_success(
        added, f"add a version to secret {secret}"
    )
    try:
        version = str(json.loads(version_payload.decode("utf-8")).get("name", ""))
    except (UnicodeDecodeError, json.JSONDecodeError):
        version = ""

    accessed = gcloud(
        [
            "secrets",
            "versions",
            "access",
            "latest",
            f"--secret={secret}",
            f"--project={project}",
        ]
    )
    stored = _require_gcloud_success(
        accessed, f"read back the latest version of secret {secret}"
    ).decode("utf-8")
    if not hmac.compare_digest(stored, candidate):
        raise SecretStoreError(
            "Secret Manager readback did not match the submitted Cursor API key"
        )
    postflight = validator(stored)
    candidate = ""
    stored = ""
    return {
        "status": "stored-and-verified",
        "provider": "cursor",
        "project": project,
        "secret": secret,
        "version": version or "latest",
        "api_key_name": postflight["api_key_name"],
        "user_email": postflight["user_email"],
        "created_at": postflight["created_at"],
        "preflight_api_key_name": preflight["api_key_name"],
    }
