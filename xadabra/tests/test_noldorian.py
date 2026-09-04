from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from xadabra.noldorian import cmd_install, main


class TestNoldorian(unittest.TestCase):
    def test_guide_exits_zero_and_points_at_pip(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(main(["guide"]), 0)
        text = buf.getvalue()
        self.assertIn("python3 -m pip install noldorian", text)
        self.assertNotIn("Everplay-Tech", text)
        self.assertNotIn("git+", text)
        self.assertNotIn("Keyabra", text)
        self.assertNotIn("pypi publish", text)

    def test_install_prints_pinned_pypi_spec(self) -> None:
        args = type("Args", (), {"run": False})()
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(cmd_install(args), 0)
        self.assertIn("noldorian==0.2.1", buf.getvalue())
        self.assertNotIn("git+", buf.getvalue())

    def test_unknown_pack_subcommand_is_gone(self) -> None:
        with patch("sys.stderr", io.StringIO()):
            with self.assertRaises(SystemExit):
                main(["pack"])


if __name__ == "__main__":
    unittest.main()
