from __future__ import annotations

import json
import subprocess
import unittest

from keyabra.discord_gcp import DiscordTokenError, store_discord_token_in_gcp


class DiscordGcpStoreTests(unittest.TestCase):
    def test_invalid_candidate_never_calls_gcloud(self) -> None:
        calls: list[object] = []

        def reject(*args: object, **kwargs: object) -> dict[str, str]:
            raise DiscordTokenError("invalid")

        def gcloud(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            calls.append((args, kwargs))
            raise AssertionError("gcloud must not be called")

        with self.assertRaises(DiscordTokenError):
            store_discord_token_in_gcp(
                "bad-token-value-that-is-long-enough",
                project="project",
                secret="secret",
                guild_id="guild",
                validator=reject,
                gcloud=gcloud,
            )
        self.assertEqual(calls, [])

    def test_success_uses_stdin_and_validates_twice(self) -> None:
        token = "valid-token-value-that-never-belongs-on-argv"
        validations: list[str] = []
        calls: list[tuple[list[str], bytes | None]] = []

        def validate(value: str, **kwargs: str) -> dict[str, str]:
            validations.append(value)
            return {
                "bot_id": "app",
                "bot_username": "relay",
                "guild_id": "guild",
                "guild_name": "control",
            }

        def gcloud(
            args: list[str],
            *,
            stdin: bytes | None = None,
        ) -> subprocess.CompletedProcess[bytes]:
            calls.append((args, stdin))
            if args[:2] == ["secrets", "describe"]:
                return subprocess.CompletedProcess(args, 0, b"{}", b"")
            if args[:3] == ["secrets", "versions", "add"]:
                payload = json.dumps(
                    {"name": "projects/p/secrets/s/versions/2"}
                ).encode()
                return subprocess.CompletedProcess(args, 0, payload, b"")
            if args[:3] == ["secrets", "versions", "access"]:
                return subprocess.CompletedProcess(args, 0, token.encode(), b"")
            raise AssertionError(args)

        receipt = store_discord_token_in_gcp(
            token,
            project="project",
            secret="secret",
            guild_id="guild",
            application_id="app",
            validator=validate,
            gcloud=gcloud,
        )

        self.assertEqual(validations, [token, token])
        self.assertEqual(receipt["status"], "stored-and-verified")
        add_call = next(
            call
            for call in calls
            if call[0][:3] == ["secrets", "versions", "add"]
        )
        self.assertEqual(add_call[1], token.encode())
        self.assertTrue(all(token not in part for args, _ in calls for part in args))


if __name__ == "__main__":
    unittest.main()
