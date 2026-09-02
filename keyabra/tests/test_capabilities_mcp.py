from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from keyabra.broker import CapabilityBroker, CapabilityStore
from keyabra.broker_server import BrokerDaemon


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
            env["PYTHONPATH"] = str(KEYABRA_ROOT / "src")
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
                        "describe_credential_capability",
                        "invoke_credential_capability",
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


if __name__ == "__main__":
    unittest.main()
