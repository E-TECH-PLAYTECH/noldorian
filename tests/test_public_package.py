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

    def list_enrollment_templates(self) -> dict[str, object]:
        return {
            "schema": "noldorian.enrollment-templates/v1",
            "templates": [{"template_id": "openai.tunnel.admin", "operations": []}],
        }

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

    def request_enrollment(
        self,
        template_id: str,
        purpose: str,
        *,
        capability_id: str | None = None,
        operations: list[str] | None = None,
        resources: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return {
            "request_id": "enroll_example",
            "status": "prompt_opened",
            "template_id": template_id,
            "purpose": purpose,
            "capability_id": capability_id or template_id,
            "operations": operations or [],
            "resources": resources or {},
        }

    def enrollment_status(self, request_id: str) -> dict[str, object]:
        return {"request_id": request_id, "status": "enrolled"}


class PublicSurfaceTests(unittest.TestCase):
    def test_client_refuses_owner_and_secret_actions(self) -> None:
        client = BrokerClient(Path("/tmp/not-used"))
        for action in (
            "enroll",
            "register",
            "import_env",
            "get_secret",
            "shell",
            "owner_prompt",
        ):
            with self.assertRaises(BrokerError):
                client._request(action)

    def test_mcp_exposes_only_public_operations(self) -> None:
        names = {tool["name"] for tool in TOOLS}
        self.assertEqual(
            names,
            {
                "doctor",
                "orient",
                "list_vault_names",
                "child_run_template",
                "broker_status",
                "list_credential_capabilities",
                "list_credential_enrollment_templates",
                "describe_credential_capability",
                "invoke_credential_capability",
                "request_credential_enrollment",
                "get_credential_enrollment_status",
            },
        )
        serialized = json.dumps(TOOLS).lower()
        for forbidden in ("register", "get_secret", "clipboard", "shell", "secret value"):
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

    def test_mcp_can_request_enrollment_without_accepting_a_credential(self) -> None:
        requests = io.StringIO(
            json.dumps(
                {
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
            )
            + "\n"
        )
        responses = io.StringIO()
        McpServer(StubClient()).serve(requests, responses)
        response = json.loads(responses.getvalue())
        self.assertFalse(response["result"]["isError"])
        body = response["result"]["content"][0]["text"]
        self.assertIn("prompt_opened", body)
        self.assertNotIn("credential", body.lower())

    def test_mcp_can_discover_reviewed_enrollment_templates(self) -> None:
        requests = io.StringIO(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "list_credential_enrollment_templates",
                        "arguments": {},
                    },
                }
            )
            + "\n"
        )
        responses = io.StringIO()
        McpServer(StubClient()).serve(requests, responses)
        response = json.loads(responses.getvalue())
        self.assertFalse(response["result"]["isError"])
        body = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(body["templates"][0]["template_id"], "openai.tunnel.admin")


if __name__ == "__main__":
    unittest.main()
