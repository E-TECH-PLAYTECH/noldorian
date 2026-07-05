from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from xadabra.cli import run_pipeline


class TestEndToEnd(unittest.TestCase):
    def test_run_with_stubbed_executor(self) -> None:
        script = "echo hello {{NAME:Your name:world}}"

        with patch("xadabra.cli.execute_script", return_value=0) as exec_mock, patch(
            "xadabra.cli.append_run"
        ):
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                code = run_pipeline(
                    script,
                    source_label="test",
                    overrides={"NAME": "world"},
                    auto_yes=True,
                )

        self.assertEqual(code, 0)
        exec_mock.assert_called_once()
        self.assertEqual(exec_mock.call_args.args[0], "echo hello world")

    def test_dry_run_no_execute(self) -> None:
        script = "echo {{X}}"
        with patch("xadabra.cli.collect_values", return_value=({"X": "1"}, set())), patch(
            "xadabra.cli.execute_script"
        ) as exec_mock:
            code = run_pipeline(script, source_label="test", dry_run=True)
        self.assertEqual(code, 0)
        exec_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
