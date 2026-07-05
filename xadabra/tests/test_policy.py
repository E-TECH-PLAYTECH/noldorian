from __future__ import annotations

import unittest

from xadabra.policy import script_uses_spells


class TestPolicy(unittest.TestCase):
    def test_detects_snx(self) -> None:
        self.assertTrue(script_uses_spells("cd /tmp && snx ios-gate"))

    def test_detects_snax_module(self) -> None:
        self.assertTrue(script_uses_spells("python3 -m snax.cli list"))

    def test_plain_shell_ok(self) -> None:
        self.assertFalse(script_uses_spells("npm test && ./deploy.sh"))

    def test_cloud_blocks_snx(self) -> None:
        from unittest.mock import patch

        from xadabra.cli import run_pipeline

        script = "snx ios-gate"
        with patch("xadabra.cli.execute_script") as run_mock:
            code = run_pipeline(script, source_label="t", cloud=True, auto_yes=True)
        self.assertEqual(code, 1)
        run_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
