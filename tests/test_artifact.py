from __future__ import annotations

import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SHIPPED_ROOTS = (
    ROOT / "src" / "noldorian",
    ROOT / "keyabra" / "src" / "keyabra",
    ROOT / "xabra" / "src" / "xabra",
    ROOT / "xadabra" / "src" / "xadabra",
    ROOT / "binabra" / "src" / "binabra",
    ROOT / "xalakazam" / "src" / "xalakazam",
)
FORBIDDEN_FILENAMES = {
    "broker.py",
    "broker_server.py",
    "broker_client.py",
    "discord_gcp.py",
    "cursor_gcp.py",
    "enrollment.py",
    "owner_prompt.py",
}
FORBIDDEN_SNIPPETS = (
    'DEFAULT_ORG = "Everplay-Tech"',
    "git+ssh://git@github.com",
    "git+https://github.com/Everplay",
    "MacBook Pro (head)",
    "dud3runner",
    "install_broker_macos",
    "pip install binabra",
    "pip install keyabra",
    "pip install xadabra",
)
FORBIDDEN_WHEEL_SUBSTRINGS = (
    "install_broker",
    "broker_server",
    "dud3runner",
    "discord_gcp",
    "cursor_gcp",
    "clipabra",
)


def _iter_shipped_text_files() -> list[Path]:
    files: list[Path] = []
    for root in SHIPPED_ROOTS:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".sh", ".md"}:
                files.append(path)
    return files


class ArtifactHygieneTests(unittest.TestCase):
    def test_shipped_sources_exclude_gondolin_server_and_private_templates(self) -> None:
        names = {path.name for path in _iter_shipped_text_files()}
        self.assertTrue(names.isdisjoint(FORBIDDEN_FILENAMES), names & FORBIDDEN_FILENAMES)

    def test_shipped_sources_exclude_private_github_and_machine_specific_copy(self) -> None:
        hits: list[str] = []
        for path in _iter_shipped_text_files():
            text = path.read_text(encoding="utf-8")
            for snippet in FORBIDDEN_SNIPPETS:
                if snippet in text:
                    hits.append(f"{path.relative_to(ROOT)}: {snippet}")
        self.assertEqual(hits, [])

    def test_readme_and_mcp_do_not_advertise_keyabra_product(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("Keyabra", readme)
        from noldorian.mcp import TOOLS

        self.assertNotIn("Keyabra", json_dumps_tools := __import__("json").dumps(TOOLS))
        self.assertNotIn("keyabra pypi", json_dumps_tools.lower())

    def test_fetch_local_does_not_require_github_cli(self) -> None:
        from xabra.core import fetch

        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / "app.dmg"
            payload.write_bytes(b"payload")
            with patch("xabra.core.require_gh", side_effect=AssertionError("gh must not be required")):
                got = fetch({"type": "local", "resolved": str(payload)}, Path(tmp))
            self.assertEqual(got, payload)

    def test_wheel_and_sdist_omit_private_surfaces_when_built(self) -> None:
        dist = ROOT / "dist"
        wheels = sorted(dist.glob("noldorian-0.2.1-py3-none-any.whl"))
        sdists = sorted(dist.glob("noldorian-0.2.1.tar.gz"))
        if not wheels and not sdists:
            self.skipTest("dist/ artifacts not built yet")
        if wheels:
            names = zipfile.ZipFile(wheels[-1]).namelist()
            blob = "\n".join(names)
            for snippet in FORBIDDEN_WHEEL_SUBSTRINGS:
                self.assertNotIn(snippet, blob)
            self.assertIn("noldorian/vault.py", names)
            self.assertIn("xabra/operator.py", names)
            self.assertIn("xadabra/cli.py", names)
            self.assertIn("xalakazam/cli.py", names)
            metadata = zipfile.ZipFile(wheels[-1]).read(
                "noldorian-0.2.1.dist-info/METADATA"
            ).decode("utf-8")
            self.assertIn("Version: 0.2.1", metadata)
            self.assertNotIn("github.com", metadata.split("Description", 1)[0])
            self.assertNotIn("Keyabra", metadata)
        if sdists:
            names = tarfile.open(sdists[-1]).getnames()
            blob = "\n".join(names)
            self.assertNotIn("clipabra/", blob)
            self.assertNotIn("install_broker_macos.sh", blob)
            self.assertNotIn("broker_server.py", blob)


if __name__ == "__main__":
    unittest.main()
