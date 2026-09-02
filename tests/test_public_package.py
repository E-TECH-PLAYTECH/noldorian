from __future__ import annotations

import io
import json
import unittest
from pathlib import Path

from noldorian.client import BrokerClient
from noldorian.errors import BrokerError
from noldorian.mcp import McpServer, TOOLS


class StubClient(BrokerClient):
    def __init__(self) -> None:
        pass

    def status(self) -> dict[str, object]:
        return {"ready": True}

    def list_capabilities(self) -> dict[str, object]:
        return {"capabilities": [{"id": "example.capability", "available": True}]}

    def describe(self, capability_id: str) -> dict[str, object]:
        return {"id": capability_id, "available": True}

    def invoke(
        self,
        capability_id: str,
        operation: str,
        arguments: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return {
            "capability_id": capability_id,
            "operation": operation,
            "arguments": arguments or {},
        }


class PublicSurfaceTests(unittest.TestCase):
    def test_client_refuses_owner_and_secret_actions(self) -> None:
        client = BrokerClient(Path("/tmp/not-used"))
        for action in ("enroll", "register", "import_env", "get_secret", "shell"):
            with self.assertRaises(BrokerError):
                client._request(action)

    def test_mcp_exposes_only_public_operations(self) -> None:
        names = {tool["name"] for tool in TOOLS}
        self.assertEqual(
            names,
            {
                "broker_status",
                "list_credential_capabilities",
                "describe_credential_capability",
                "invoke_credential_capability",
            },
        )
        serialized = json.dumps(TOOLS).lower()
        for forbidden in ("enroll", "register", "get_secret", "clipboard", "shell"):
            self.assertNotIn(forbidden, serialized)

    def test_mcp_round_trip_contains_no_internal_exception_detail(self) -> None:
        requests = io.StringIO(
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n"
            + json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "invoke_credential_capability",
                        "arguments": {
                            "capability_id": "example.capability",
                            "operation": "example.run",
                            "arguments": {"value": "public"},
                        },
                    },
                }
            )
            + "\n"
        )
        responses = io.StringIO()
        McpServer(StubClient()).serve(requests, responses)
        lines = [json.loads(line) for line in responses.getvalue().splitlines()]
        self.assertEqual(lines[0]["result"]["tools"], TOOLS)
        self.assertFalse(lines[1]["result"]["isError"])
        self.assertIn("example.run", lines[1]["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
