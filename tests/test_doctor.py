from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from noldorian.cli import main as noldorian_main
from noldorian.doctor import doctor_report
from noldorian.mcp import McpServer, TOOLS
from noldorian.vault import child_run_template


class DoctorTests(unittest.TestCase):
    def test_doctor_ok_without_socket(self) -> None:
        report = doctor_report(socket_path=Path("/tmp/noldorian-no-such-broker.sock"))
        self.assertEqual(report["schema"], "noldorian.doctor/v1")
        self.assertEqual(report["version"], "0.2.1")
        self.assertEqual(report["extension"]["status"], "absent")
        self.assertTrue(report["ok"])
        self.assertIn("pip install noldorian", report["install"])

    def test_cli_doctor_prints_json(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = noldorian_main(["doctor"])
        self.assertEqual(code, 0)
        body = json.loads(buf.getvalue())
        self.assertEqual(body["schema"], "noldorian.doctor/v1")
        self.assertEqual(body["extension"]["status"], "absent")

    def test_mcp_doctor_without_socket(self) -> None:
        requests = io.StringIO(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "doctor", "arguments": {}},
                }
            )
            + "\n"
        )
        responses = io.StringIO()
        McpServer().serve(requests, responses)
        response = json.loads(responses.getvalue())
        self.assertFalse(response["result"]["isError"])
        body = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(body["schema"], "noldorian.doctor/v1")
        serialized = json.dumps(body)
        self.assertNotIn("secret value", serialized.lower())

    def test_mcp_list_vault_names_no_values(self) -> None:
        secret = "mcp-secret-sentinel"
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault.env"
            vault.write_text(f"TOKEN={secret}\n")
            os.chmod(vault, 0o600)
            with patch("noldorian.mcp.default_vault_path", return_value=vault):
                requests = io.StringIO(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/call",
                            "params": {"name": "list_vault_names", "arguments": {}},
                        }
                    )
                    + "\n"
                )
                responses = io.StringIO()
                McpServer().serve(requests, responses)
        response = json.loads(responses.getvalue())
        body = json.loads(response["result"]["content"][0]["text"])
        self.assertIn("TOKEN", body["names"])
        self.assertNotIn(secret, json.dumps(body))

    def test_child_run_template_has_no_secret(self) -> None:
        template = child_run_template("deploy.sh")
        self.assertIn("xabra run --env-file", template["command"])
        blob = json.dumps(template)
        self.assertNotIn("TOKEN=", blob)

    def test_tools_forbid_secret_value_wording(self) -> None:
        serialized = json.dumps(TOOLS).lower()
        for forbidden in ("register", "get_secret", "secret value"):
            self.assertNotIn(forbidden, serialized)
