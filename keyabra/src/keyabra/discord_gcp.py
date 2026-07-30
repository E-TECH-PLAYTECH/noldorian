"""Validate a Discord bot token and store it in Google Secret Manager.

The token is accepted through an in-process prompt, sent to Discord in an HTTP
header, and sent to gcloud over stdin. It is never placed on argv, written to a
temporary file, or included in a receipt.
"""

from __future__ import annotations

import hmac
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from typing import Any, Callable


DISCORD_API = "https://discord.com/api/v10"


class DiscordTokenError(RuntimeError):
    """A candidate token failed identity or guild validation."""


class SecretStoreError(RuntimeError):
    """Google Secret Manager could not store or return the token."""


def _discord_get(
    token: str,
    path: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{DISCORD_API}{path}",
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "keyabra-discord-token-rite/1",
        },
    )
    try:
        with opener(request, timeout=20) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise DiscordTokenError(
                    f"Discord rejected {path} with HTTP {status}"
                )
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise DiscordTokenError(
            f"Discord rejected {path} with HTTP {exc.code}"
        ) from None
    except urllib.error.URLError as exc:
        raise DiscordTokenError(
            f"Discord could not be reached while validating {path}: {exc.reason}"
        ) from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise DiscordTokenError(
            f"Discord returned an unreadable response for {path}"
        ) from None
    if not isinstance(payload, dict):
        raise DiscordTokenError(f"Discord returned an invalid response for {path}")
    return payload


def validate_discord_token(
    token: str,
    *,
    guild_id: str,
    application_id: str | None = None,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, str]:
    """Require a bot identity and membership in the intended Discord guild."""
    candidate = token.strip()
    if not candidate:
        raise DiscordTokenError("Discord token is empty")

    bot = _discord_get(candidate, "/users/@me", opener=opener)
    guild = _discord_get(candidate, f"/guilds/{guild_id}", opener=opener)
    bot_id = str(bot.get("id", ""))
    actual_guild_id = str(guild.get("id", ""))
    if not bot_id or not bool(bot.get("bot")):
        raise DiscordTokenError("credential is not a Discord bot token")
    if application_id and bot_id != application_id:
        raise DiscordTokenError(
            f"token belongs to bot {bot_id}, expected application {application_id}"
        )
    if actual_guild_id != guild_id:
        raise DiscordTokenError(
            f"token reached guild {actual_guild_id or '<unknown>'}, expected {guild_id}"
        )
    return {
        "bot_id": bot_id,
        "bot_username": str(bot.get("username", "")),
        "guild_id": actual_guild_id,
        "guild_name": str(guild.get("name", "")),
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


def store_discord_token_in_gcp(
    token: str,
    *,
    project: str,
    secret: str,
    guild_id: str,
    application_id: str | None = None,
    validator: Callable[..., dict[str, str]] = validate_discord_token,
    gcloud: Callable[..., subprocess.CompletedProcess[bytes]] = _run_gcloud,
) -> dict[str, str]:
    """Validate, store via stdin, read back, and validate again."""
    candidate = token.strip()
    preflight = validator(
        candidate,
        guild_id=guild_id,
        application_id=application_id,
    )

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
            "Secret Manager readback did not match the submitted token"
        )
    postflight = validator(
        stored,
        guild_id=guild_id,
        application_id=application_id,
    )
    candidate = ""
    stored = ""
    return {
        "status": "stored-and-verified",
        "project": project,
        "secret": secret,
        "version": version or "latest",
        "bot_id": postflight["bot_id"],
        "bot_username": postflight["bot_username"],
        "guild_id": postflight["guild_id"],
        "guild_name": postflight["guild_name"],
        "preflight_bot_id": preflight["bot_id"],
    }
