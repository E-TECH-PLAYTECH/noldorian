from __future__ import annotations

import json
import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from xabra.macos_keychain import _codesign_probe, unlock_keychain_from_vault


def write_vault(path: Path, text: str) -> Path:
    path.write_text(text)
    os.chmod(path, 0o600)
    return path


class MacOSKeychainTests(unittest.TestCase):
    def test_unlock_uses_secret_without_disclosing_it(self) -> None:
        secret = "login-password-sentinel"
        with self._tmp() as tmp:
            vault = write_vault(tmp / "vault.env", f"LOGIN={secret}\n")
            keychain = tmp / "login.keychain-db"
            keychain.touch()
            calls: list[tuple[Path, str]] = []
            probes: list[str] = []

            receipt = unlock_keychain_from_vault(
                vault=vault,
                credential_name="LOGIN",
                keychain=keychain,
                probe_identity="IDENTITY-HASH",
                unlocker=lambda path, password: calls.append((path, password)),
                probe_runner=probes.append,
            )

            self.assertEqual(calls, [(keychain.resolve(), secret)])
            self.assertEqual(probes, ["IDENTITY-HASH"])
            self.assertTrue(receipt["unlocked"])
            self.assertTrue(receipt["codesign_probe"]["passed"])
            self.assertNotIn(secret, json.dumps(receipt, sort_keys=True))

    def test_unlock_does_not_execute_unrelated_provider(self) -> None:
        with self._tmp() as tmp:
            vault = write_vault(
                tmp / "vault.env",
                "ORG_PAT__CMD=exit 1\nLOGIN=login-password-sentinel\n",
            )
            keychain = tmp / "login.keychain-db"
            keychain.touch()
            passwords: list[str] = []

            receipt = unlock_keychain_from_vault(
                vault=vault,
                credential_name="LOGIN",
                keychain=keychain,
                probe_identity="IDENTITY-HASH",
                unlocker=lambda _path, password: passwords.append(password),
                probe_runner=lambda _identity: None,
            )

            self.assertEqual(passwords, ["login-password-sentinel"])
            self.assertTrue(receipt["codesign_probe"]["passed"])

    def test_unlock_without_probe_is_explicit(self) -> None:
        with self._tmp() as tmp:
            vault = write_vault(tmp / "vault.env", "LOGIN=sentinel\n")
            keychain = tmp / "login.keychain-db"
            keychain.touch()

            receipt = unlock_keychain_from_vault(
                vault=vault,
                credential_name="LOGIN",
                keychain=keychain,
                unlocker=lambda _path, _password: None,
            )

            self.assertEqual(
                receipt["codesign_probe"],
                {"attempted": False, "identity": None, "passed": False},
            )

    def test_unlock_fails_for_missing_or_empty_secret(self) -> None:
        for contents in ("OTHER=value\n", "LOGIN=\n"):
            with self.subTest(contents=contents):
                with self._tmp() as tmp:
                    vault = write_vault(tmp / "vault.env", contents)
                    keychain = tmp / "login.keychain-db"
                    keychain.touch()
                    with self.assertRaises((KeyError, ValueError)):
                        unlock_keychain_from_vault(
                            vault=vault,
                            credential_name="LOGIN",
                            keychain=keychain,
                            unlocker=lambda _path, _password: None,
                        )

    def test_probe_failure_does_not_disclose_secret(self) -> None:
        secret = "probe-failure-sentinel"
        with self._tmp() as tmp:
            vault = write_vault(tmp / "vault.env", f"LOGIN={secret}\n")
            keychain = tmp / "login.keychain-db"
            keychain.touch()

            def fail_probe(_identity: str) -> None:
                raise RuntimeError("codesign probe failed")

            with self.assertRaises(RuntimeError) as error:
                unlock_keychain_from_vault(
                    vault=vault,
                    credential_name="LOGIN",
                    keychain=keychain,
                    probe_identity="IDENTITY-HASH",
                    unlocker=lambda _path, _password: None,
                    probe_runner=fail_probe,
                )
            self.assertNotIn(secret, str(error.exception))

    def test_codesign_probe_does_not_copy_sip_metadata(self) -> None:
        with patch.object(shutil, "which", lambda _name: "/usr/bin/true"):
            _codesign_probe("IDENTITY-HASH")

    def _tmp(self):
        import tempfile
        from contextlib import contextmanager

        @contextmanager
        def wrapped():
            with tempfile.TemporaryDirectory() as raw:
                yield Path(raw)

        return wrapped()


if __name__ == "__main__":
    unittest.main()
