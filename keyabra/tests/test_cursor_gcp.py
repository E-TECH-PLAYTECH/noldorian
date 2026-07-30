from __future__ import annotations

import json
import subprocess
import unittest

from keyabra.cursor_gcp import (
    CursorApiKeyError,
    store_cursor_api_key_in_gcp,
    validate_cursor_api_key,
)


class CursorGcpStoreTests(unittest.TestCase):
    def test_invalid_candidate_never_calls_gcloud(self) -> None:
        calls: list[object] = []

        def reject(value: str) -> dict[str, str]:
            raise CursorApiKeyError("invalid")

        def gcloud(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            calls.append((args, kwargs))
            raise AssertionError("gcloud must not be called")

        with self.assertRaises(CursorApiKeyError):
            store_cursor_api_key_in_gcp(
                "bad-cursor-key-value",
                project="project",
                secret="secret",
                validator=reject,
                gcloud=gcloud,
            )
        self.assertEqual(calls, [])

    def test_success_uses_stdin_and_validates_twice(self) -> None:
        api_key = "crsr_valid-key-that-never-belongs-on-argv"
        validations: list[str] = []
        calls: list[tuple[list[str], bytes | None]] = []

        def validate(value: str) -> dict[str, str]:
            validations.append(value)
            return {
                "api_key_name": "Everplay SDK",
                "user_email": "owner@example.com",
                "created_at": "2026-07-30T00:00:00Z",
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
                    {"name": "projects/p/secrets/s/versions/1"}
                ).encode()
                return subprocess.CompletedProcess(args, 0, payload, b"")
            if args[:3] == ["secrets", "versions", "access"]:
                return subprocess.CompletedProcess(args, 0, api_key.encode(), b"")
            raise AssertionError(args)

        receipt = store_cursor_api_key_in_gcp(
            api_key,
            project="project",
            secret="secret",
            validator=validate,
            gcloud=gcloud,
        )

        self.assertEqual(validations, [api_key, api_key])
        self.assertEqual(receipt["status"], "stored-and-verified")
        self.assertEqual(receipt["provider"], "cursor")
        add_call = next(
            call
            for call in calls
            if call[0][:3] == ["secrets", "versions", "add"]
        )
        self.assertEqual(add_call[1], api_key.encode())
        self.assertTrue(all(api_key not in part for args, _ in calls for part in args))

    def test_live_validator_requires_cursor_identity(self) -> None:
        class Response:
            status = 200

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"userEmail":"owner@example.com"}'

        with self.assertRaises(CursorApiKeyError):
            validate_cursor_api_key(
                "crsr_candidate-key-value",
                opener=lambda *args, **kwargs: Response(),
            )


if __name__ == "__main__":
    unittest.main()
