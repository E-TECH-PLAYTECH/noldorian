from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from xadabra.cli import run_pipeline
from xadabra.fills import collect_values, parse_set_args, prefill_placeholder
from xadabra.parser import parse_placeholder_inner


class TestCloudFills(unittest.TestCase):
    def test_parse_set(self) -> None:
        self.assertEqual(parse_set_args(["A=1", "B=two"]), {"A": "1", "B": "two"})

    def test_prefill_from_env(self) -> None:
        ph = parse_placeholder_inner("TOKEN")
        with patch.dict(os.environ, {"XADABRA_TOKEN": "abc"}):
            self.assertEqual(prefill_placeholder(ph, {}), "abc")

    def test_cloud_missing_exits(self) -> None:
        ph = parse_placeholder_inner("MISSING")
        with self.assertRaises(SystemExit):
            collect_values([ph], overrides={}, cloud=True)

    def test_cloud_with_set(self) -> None:
        ph = parse_placeholder_inner("WHO:Name?:world")
        values, secrets = collect_values([ph], overrides={"WHO": "ada"}, cloud=True)
        self.assertEqual(values["WHO"], "ada")
        self.assertEqual(secrets, set())

    def test_cloud_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ph = parse_placeholder_inner("DIR|path:Dir")
            values, _ = collect_values([ph], overrides={"DIR": tmp}, cloud=True)
            self.assertEqual(Path(values["DIR"]).resolve(), Path(tmp).resolve())


class TestCloudRun(unittest.TestCase):
    def test_cloud_pipeline(self) -> None:
        script = "echo {{MSG:Message?:hi}}"
        with patch("xadabra.cli.execute_script", return_value=0) as run_mock, patch(
            "xadabra.cli.append_run"
        ):
            code = run_pipeline(
                script,
                source_label="test",
                cloud=True,
                overrides={"MSG": "cloud"},
            )
        self.assertEqual(code, 0)
        self.assertEqual(run_mock.call_args.args[0], "echo cloud")


if __name__ == "__main__":
    unittest.main()
