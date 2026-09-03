from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from keyabra.broker import CapabilityBroker, CapabilityStore
from keyabra.broker_server import BrokerDaemon
from keyabra.enrollment import HumanEnrollmentGate


KEYABRA_ROOT = Path(__file__).resolve().parents[1]
NOLDORIAN_ROOT = Path(__file__).resolve().parents[2]
MCP_SERVER = NOLDORIAN_ROOT / "mcp" / "noldorian_capabilities_mcp.py"


class CapabilitiesMcpTests(unittest.TestCase):
    def test_mcp_lists_only_public_capability_data(self) -> None:
        secret = b"mcp-secret-value-never-returned"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = CapabilityStore(root / "state")
            store.register(
                {
                    "id": "openai.tunnel.admin",
                    "provider": "openai",
                    "description": "Manage OpenAI Secure MCP Tunnels",
                    "adapter": "openai_tunnel_admin",
                    "operations": ["tunnels.list"],
                    "resources": {"organization_ids": ["org_example"]},
                }
            )
            store.enroll("openai.tunnel.admin", secret)
            broker = CapabilityBroker(store, tunnel_client_bin="/bin/echo")
            uid = os.getuid()
            daemon = BrokerDaemon(
                root / "broker.sock",
                broker,
                allowed_uids={uid},
                owner_uids={uid},
                socket_mode=0o600,
            )
            thread = threading.Thread(target=daemon.serve_forever, daemon=True)
            thread.start()
            env = os.environ.copy()
            env["NOLDORIAN_BROKER_SOCKET"] = str(root / "broker.sock")
            env["PYTHONPATH"] = os.pathsep.join(
                [str(NOLDORIAN_ROOT / "src"), str(KEYABRA_ROOT / "src")]
            )
            process = subprocess.Popen(
                [sys.executable, str(MCP_SERVER)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            try:
                assert process.stdin is not None
                assert process.stdout is not None
                requests = [
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05"},
                    },
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "list_credential_capabilities",
                            "arguments": {},
                        },
                    },
                ]
                for request in requests:
                    process.stdin.write(json.dumps(request) + "\n")
                process.stdin.flush()
                responses = [json.loads(process.stdout.readline()) for _ in range(3)]
                serialized = json.dumps(responses)
                self.assertNotIn(secret.decode(), serialized)
                tool_names = [tool["name"] for tool in responses[1]["result"]["tools"]]
                self.assertEqual(
                    tool_names,
                    [
                        "broker_status",
                        "list_credential_capabilities",
                        "list_credential_enrollment_templates",
                        "describe_credential_capability",
                        "invoke_credential_capability",
                        "request_credential_enrollment",
                        "get_credential_enrollment_status",
                    ],
                )
                self.assertNotIn("get_secret", serialized)
            finally:
                process.terminate()
                process.wait(timeout=5)
                if process.stdin is not None:
                    process.stdin.close()
                if process.stdout is not None:
                    process.stdout.close()
                if process.stderr is not None:
                    process.stderr.close()
                daemon.shutdown()
                daemon.server_close()
                thread.join(timeout=2)

    def test_mcp_request_starts_human_gate_and_returns_only_terminal_status(self) -> None:
        secret = b"mcp-human-gate-secret-never-returned"

        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "status": "approved",
                        "secret_b64": base64.b64encode(secret).decode("ascii"),
                    }
                ),
                "",
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = CapabilityStore(root / "state")
            broker = CapabilityBroker(store, tunnel_client_bin="/bin/echo")
            gate = HumanEnrollmentGate(
                prompt_uid=os.getuid(),
                prompt_python=sys.executable,
                prompt_app=sys.executable,
                launchctl_bin=sys.executable,
                runner=runner,
            )
            daemon = BrokerDaemon(
                root / "broker.sock",
                broker,
                allowed_uids={os.getuid()},
                owner_uids={os.getuid()},
                socket_mode=0o600,
                enrollment_gate=gate,
            )
            thread = threading.Thread(target=daemon.serve_forever, daemon=True)
            thread.start()
            env = os.environ.copy()
            env["NOLDORIAN_BROKER_SOCKET"] = str(root / "broker.sock")
            env["PYTHONPATH"] = os.pathsep.join(
                [str(NOLDORIAN_ROOT / "src"), str(KEYABRA_ROOT / "src")]
            )
            process = subprocess.Popen(
                [sys.executable, str(MCP_SERVER)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            try:
                assert process.stdin is not None
                assert process.stdout is not None
                request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "request_credential_enrollment",
                        "arguments": {
                            "template_id": "openai.tunnel.admin",
                            "purpose": "Studio Bridge administration",
                        },
                    },
                }
                process.stdin.write(json.dumps(request) + "\n")
                process.stdin.flush()
                response = json.loads(process.stdout.readline())
                body = json.loads(response["result"]["content"][0]["text"])
                self.assertFalse(response["result"]["isError"])
                request_id = body["request_id"]
                self.assertEqual(body["status"], "awaiting_human")

                terminal = body
                for poll_id in range(2, 52):
                    process.stdin.write(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": poll_id,
                                "method": "tools/call",
                                "params": {
                                    "name": "get_credential_enrollment_status",
                                    "arguments": {"request_id": request_id},
                                },
                            }
                        )
                        + "\n"
                    )
                    process.stdin.flush()
                    polled = json.loads(process.stdout.readline())
                    terminal = json.loads(polled["result"]["content"][0]["text"])
                    if terminal["status"] in {"enrolled", "failed", "cancelled"}:
                        break
                    time.sleep(0.01)
                self.assertEqual(terminal["status"], "enrolled")
                self.assertNotIn(secret.decode(), json.dumps(response))
                self.assertNotIn(secret.decode(), json.dumps(terminal))
            finally:
                process.terminate()
                process.wait(timeout=5)
                if process.stdin is not None:
                    process.stdin.close()
                if process.stdout is not None:
                    process.stdout.close()
                if process.stderr is not None:
                    process.stderr.close()
                daemon.shutdown()
                daemon.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
