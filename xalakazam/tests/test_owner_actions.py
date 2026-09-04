from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from noldorian import vault as vault_mod
from xalakazam import OWNER_ACTIONS
from xalakazam.cli import main


class OwnerActionRiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        env_patch = patch.object(vault_mod, "ENV_DIR", root / "noldorian")
        legacy_patch = patch.object(vault_mod, "LEGACY_ENV_DIR", root / "keyabra")
        env_patch.start()
        legacy_patch.start()
        self.addCleanup(env_patch.stop)
        self.addCleanup(legacy_patch.stop)

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
