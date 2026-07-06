from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from xadabra.noldorian import cmd_pack, main


class TestNoldorian(unittest.TestCase):
    def test_pack_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            projects = root / "Projects"
            for name in ("binabra", "keyabra", "xadabra"):
                pkg = projects / name
                pkg.mkdir(parents=True)
                (pkg / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

            dest = root / "noldorian"
            args = type(
                "Args",
                (),
                {
                    "dest": str(dest),
                    "projects_dir": str(projects),
                    "org": "Everplay-Tech",
                    "repo": "noldorian",
                    "tag": "v0.1.1",
                    "force": False,
                },
            )()
            self.assertEqual(cmd_pack(args), 0)
            self.assertTrue((dest / "binabra").is_dir())
            self.assertTrue((dest / "README.md").is_file())
            self.assertIn("Everplay-Tech", (dest / "README.md").read_text(encoding="utf-8"))

    def test_guide_exits_zero(self) -> None:
        with patch("builtins.print"):
            self.assertEqual(main(["guide"]), 0)


if __name__ == "__main__":
    unittest.main()
