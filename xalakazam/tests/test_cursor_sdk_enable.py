from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from xalakazam.cli import _cmd_cursor_sdk_enable


class CursorSdkEnableTests(unittest.TestCase):
    @patch("xalakazam.cli._wait")
    @patch("xalakazam.cli.subprocess.run")
    @patch("xalakazam.cli.shutil.which", return_value="/usr/local/bin/keyabra")
    def test_hands_secret_intake_to_keyabra(
        self,
        which: object,
        run: object,
        wait: object,
    ) -> None:
        run.return_value = subprocess.CompletedProcess([], 0)

        result = _cmd_cursor_sdk_enable(["--no-open"])

        self.assertEqual(result, 0)
        run.assert_called_once_with(
            [
                "/usr/local/bin/keyabra",
                "cursor",
                "gcp-store",
                "--project",
                "everplay-centaur-chess",
                "--secret",
                "everplay-cursor-sdk-api-key",
            ],
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
