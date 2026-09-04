from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from noldorian import vault as vault_mod
from noldorian.vault import (
    load_env_file,
    load_env_value,
    probe_env_file,
    run_with_env,
)
from xabra.cli import main as xabra_main
from xabra.operator import main as operator_main


def write_vault(path: Path, text: str) -> Path:
    path.write_text(text)
    os.chmod(path, 0o600)
    return path


class IsolatedHomeMixin:
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.env_dir = root / "noldorian"
        self.legacy_dir = root / "keyabra"
        env_patch = mock.patch.object(vault_mod, "ENV_DIR", self.env_dir)
        legacy_patch = mock.patch.object(vault_mod, "LEGACY_ENV_DIR", self.legacy_dir)
        env_patch.start()
        legacy_patch.start()
        self.addCleanup(env_patch.stop)
        self.addCleanup(legacy_patch.stop)


class VaultContractTests(IsolatedHomeMixin, unittest.TestCase):
    def test_probe_direct_value_returns_metadata_without_secret(self) -> None:
        secret = "direct-secret-sentinel"
        with tempfile.TemporaryDirectory() as tmp:
            vault = write_vault(Path(tmp) / "vault.env", f"TOKEN={secret}\n")
            receipt = probe_env_file(vault, "TOKEN")
            encoded = json.dumps(receipt, sort_keys=True)
            self.assertEqual(receipt["schema"], "noldorian.env-probe/v1")
            self.assertTrue(receipt["present"])
            self.assertNotIn(secret, encoded)

    def test_probe_does_not_execute_unrelated_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = write_vault(
                Path(tmp) / "vault.env",
                "UNRELATED__CMD=exit 7\nTOKEN=target-secret\n",
            )
            receipt = probe_env_file(vault, "TOKEN")
            self.assertTrue(receipt["present"])

    def test_selective_load_fails_closed_for_multiple_providers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = write_vault(
                Path(tmp) / "vault.env",
                "TOKEN=direct\nTOKEN__CMD=printf command\n",
            )
            with self.assertRaises(ValueError):
                load_env_value(vault, "TOKEN")

    def test_probe_fails_closed_for_unsafe_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = write_vault(Path(tmp) / "vault.env", "TOKEN=sentinel\n")
            os.chmod(vault, 0o644)
            with self.assertRaises(PermissionError):
                probe_env_file(vault, "TOKEN")

    def test_failed_command_does_not_echo_command_stderr(self) -> None:
        secret = "stderr-secret-sentinel"
        with tempfile.TemporaryDirectory() as tmp:
            vault = write_vault(
                Path(tmp) / "vault.env",
                f"TOKEN__CMD=printf '{secret}' >&2; exit 7\n",
            )
            with self.assertRaises(RuntimeError) as error:
                load_env_file(vault)
            self.assertIn("exit 7", str(error.exception))
            self.assertNotIn(secret, str(error.exception))

    def test_run_with_env_puts_secret_in_child_not_argv(self) -> None:
        secret = "child-env-sentinel"
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "out.txt"
            code = run_with_env(
                [
                    "python3",
                    "-c",
                    f"import os; open({str(marker)!r}, 'w').write(os.environ['TOKEN'])",
                ],
                {"TOKEN": secret},
            )
            self.assertEqual(code, 0)
            self.assertEqual(marker.read_text(), secret)

    def test_xabra_env_probe_cli_emits_json_without_secret(self) -> None:
        secret = "cli-secret-sentinel"
        with tempfile.TemporaryDirectory() as tmp:
            vault = write_vault(Path(tmp) / "vault.env", f"TOKEN={secret}\n")
            self.assertEqual(
                operator_main(["env", "probe", "TOKEN", "--file", str(vault)]),
                0,
            )

    def test_xabra_dispatches_run_subcommand(self) -> None:
        secret = "dispatch-sentinel"
        with tempfile.TemporaryDirectory() as tmp:
            vault = write_vault(Path(tmp) / "vault.env", f"TOKEN={secret}\n")
            marker = Path(tmp) / "out.txt"
            script = (
                "import os,sys; open(sys.argv[1],'w').write(os.environ['TOKEN'])"
            )
            code = xabra_main(
                [
                    "run",
                    "--env-file",
                    str(vault),
                    "--",
                    "python3",
                    "-c",
                    script,
                    str(marker),
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual(marker.read_text(), secret)

    def test_xabra_has_no_pypi_subcommand(self) -> None:
        from xabra.operator import help_text

        self.assertNotIn("pypi", help_text())
        self.assertEqual(operator_main(["pypi", "publish", "."]), 1)

    def test_builtin_app_catalog_is_empty(self) -> None:
        from xabra import BUILTIN_APPS

        self.assertEqual(BUILTIN_APPS, {})

    def test_default_vault_path_prefers_canonical(self) -> None:
        from noldorian import vault as vault_mod

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            canonical_dir = home / ".config" / "noldorian"
            legacy_dir = home / ".config" / "keyabra"
            canonical_dir.mkdir(parents=True)
            legacy_dir.mkdir(parents=True)
            canonical = write_vault(canonical_dir / "vault.env", "TOKEN=canonical\n")
            write_vault(legacy_dir / "keyabra.env", "TOKEN=legacy\n")
            with mock.patch.object(vault_mod, "ENV_DIR", canonical_dir), mock.patch.object(
                vault_mod, "LEGACY_ENV_DIR", legacy_dir
            ):
                self.assertEqual(vault_mod.default_vault_path(), canonical)

    def test_default_vault_path_falls_back_to_legacy(self) -> None:
        from noldorian import vault as vault_mod

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            canonical_dir = home / ".config" / "noldorian"
            legacy_dir = home / ".config" / "keyabra"
            canonical_dir.mkdir(parents=True)
            legacy_dir.mkdir(parents=True)
            legacy = write_vault(legacy_dir / "keyabra.env", "TOKEN=legacy\n")
            with mock.patch.object(vault_mod, "ENV_DIR", canonical_dir), mock.patch.object(
                vault_mod, "LEGACY_ENV_DIR", legacy_dir
            ):
                self.assertEqual(vault_mod.default_vault_path(), legacy)

    def test_ensure_canonical_home_creates_empty_vault_without_leftover(self) -> None:
        created = vault_mod.ensure_canonical_home()
        self.assertEqual(created, self.env_dir / "vault.env")
        self.assertTrue(created.is_file())
        self.assertEqual(oct(self.env_dir.stat().st_mode & 0o777), "0o700")
        self.assertEqual(oct(created.stat().st_mode & 0o777), "0o600")
        text = created.read_text()
        self.assertTrue(text.startswith("# Noldorian vault"))
        self.assertFalse(any("=" in line and not line.startswith("#") for line in text.splitlines()))
        self.assertFalse((self.legacy_dir / "keyabra.env").exists())
        self.assertFalse(self.legacy_dir.exists())

    def test_ensure_canonical_home_does_not_copy_or_hide_leftover(self) -> None:
        self.legacy_dir.mkdir(parents=True)
        leftover = write_vault(self.legacy_dir / "keyabra.env", "TOKEN=leftover-sentinel\n")
        created = vault_mod.ensure_canonical_home()
        self.assertEqual(created, leftover)
        self.assertFalse((self.env_dir / "vault.env").exists())
        self.assertEqual(leftover.read_text(), "TOKEN=leftover-sentinel\n")
        self.assertTrue(vault_mod.leftover_blocks_canonical())
