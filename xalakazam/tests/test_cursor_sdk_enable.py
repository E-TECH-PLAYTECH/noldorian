from __future__ import annotations

import io
import subprocess
import unittest
from contextlib import redirect_stdout
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

        output = io.StringIO()
        with redirect_stdout(output):
            result = _cmd_cursor_sdk_enable(
                [
                    "--project",
                    "example-project",
                    "--secret",
                    "example-cursor-api-key",
                    "--no-open",
                ]
            )

        self.assertEqual(result, 0)
        self.assertIn("Internal evaluation only", output.getvalue())
        self.assertIn("does not install, license, or grant", output.getvalue())
        run.assert_called_once_with(
            [
                "/usr/local/bin/keyabra",
                "cursor",
                "gcp-store",
                "--project",
                "example-project",
                "--secret",
                "example-cursor-api-key",
            ],
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
