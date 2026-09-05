from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from noldorian import vault as vault_mod
from noldorian.cli import main as noldorian_main
from noldorian.update import parse_version, pypi_status, run_upgrade, upgrade_argv


class UpdateTests(unittest.TestCase):
    def test_parse_version_orders_releases(self) -> None:
        self.assertLess(parse_version("0.2.2"), parse_version("0.2.3"))
        self.assertFalse(parse_version("0.2.3") > parse_version("0.2.3"))

    def test_pypi_status_reports_newer_without_installing(self) -> None:
        payload = json.dumps({"info": {"version": "0.2.3"}}).encode()

        class _Resp:
            def read(self) -> bytes:
                return payload

            def __enter__(self) -> "_Resp":
                return self

            def __exit__(self, *args: object) -> None:
                return None

        with patch("noldorian.update.urllib.request.urlopen", return_value=_Resp()):
            report = pypi_status("0.2.2")
        self.assertTrue(report["update_available"])
        self.assertEqual(report["pypi_latest"], "0.2.3")
        self.assertFalse(report["auto_update"])
        self.assertTrue(report["vault_persists"])
        self.assertIn("pypi.org/simple", report["index"])

    def test_upgrade_without_confirm_does_not_run_pip(self) -> None:
        with patch("noldorian.update.subprocess.run") as run:
            receipt = run_upgrade(confirm=False)
        run.assert_not_called()
        self.assertTrue(receipt["ok"])
        self.assertTrue(receipt["vault_persists"])
        self.assertIn("pypi.org/simple", " ".join(receipt["command"]))

    def test_upgrade_confirm_downloads_from_pypi_index(self) -> None:
        with patch("noldorian.update.subprocess.run") as run:
            run.return_value.returncode = 0
            receipt = run_upgrade(confirm=True)
        run.assert_called_once()
        argv = run.call_args[0][0]
        self.assertTrue(receipt["ok"])
        self.assertIn("https://pypi.org/simple", " ".join(argv))
        self.assertTrue(all(not part.endswith(".whl") for part in argv))

    def test_cli_upgrade_json_has_no_secret(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(vault_mod, "ENV_DIR", root / "noldorian"), patch.object(
                vault_mod, "LEGACY_ENV_DIR", root / "keyabra"
            ), patch("sys.stdout", buf), patch("noldorian.update.subprocess.run") as run:
                code = noldorian_main(["upgrade"])
        run.assert_not_called()
        self.assertEqual(code, 0)
        body = json.loads(buf.getvalue())
        self.assertEqual(body["schema"], "noldorian.upgrade/v1")
        self.assertNotIn("TOKEN=", json.dumps(body))

    def test_upgrade_argv_never_points_at_a_local_wheel(self) -> None:
        argv = upgrade_argv()
        blob = " ".join(argv)
        self.assertNotIn(".whl", blob)
        self.assertNotIn("dist/", blob)
        self.assertIn("pypi.org/simple", blob)
