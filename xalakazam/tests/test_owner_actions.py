from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from xalakazam import OWNER_ACTIONS
from xalakazam.cli import main


class OwnerActionRiteTests(unittest.TestCase):
    def test_playbook_contains_pause_and_secret_boundary(self) -> None:
        self.assertIn("OWNER CHECKPOINT", OWNER_ACTIONS)
        self.assertIn("purchase <product>", OWNER_ACTIONS)
        self.assertIn("xabra", OWNER_ACTIONS)
        self.assertIn("noldorian.owner-action-checkpoint/v1", OWNER_ACTIONS)

    def test_cli_exposes_owner_action_playbook(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["--owner-actions"])

        self.assertEqual(result, 0)
        self.assertIn("no repeated probe", output.getvalue())


if __name__ == "__main__":
    unittest.main()
