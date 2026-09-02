"""Zero-dependency MCP server for public Noldorian capability operations."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TextIO

from noldorian import __version__
from noldorian.client import BrokerClient, DEFAULT_SOCKET_PATH
from noldorian.errors import BrokerError


TOOLS = [
    {
        "name": "broker_status",
        "description": "Check whether the local Noldorian capability broker is ready.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "list_credential_capabilities",
        "description": (
            "List providers, approved operations, resources, and availability without "
            "returning credential values or custody paths."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "describe_credential_capability",
        "description": "Describe one credential capability without revealing its secret.",
        "inputSchema": {
            "type": "object",
            "properties": {"capability_id": {"type": "string", "minLength": 1}},
            "required": ["capability_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "invoke_credential_capability",
        "description": "Invoke one fixed operation approved for a credential capability.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "capability_id": {"type": "string", "minLength": 1},
                "operation": {"type": "string", "minLength": 1},
                "arguments": {"type": "object"},
            },
            "required": ["capability_id", "operation"],
            "additionalProperties": False,
        },
    },
]


class McpServer:
    """Small JSON-RPC loop around a public-only :class:`BrokerClient`."""

    def __init__(self, client: Optional[BrokerClient] = None) -> None:
        self.client = client or BrokerClient(DEFAULT_SOCKET_PATH)
        self.dispatch: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            "broker_status": lambda _args: self.client.status(),
            "list_credential_capabilities": lambda _args: self.client.list_capabilities(),
            "describe_credential_capability": self._describe,
            "invoke_credential_capability": self._invoke,
        }

    def _describe(self, args: Dict[str, Any]) -> Dict[str, Any]:
        capability_id = args.get("capability_id")
        if not isinstance(capability_id, str) or not capability_id.strip():
            raise BrokerError("capability_id is required")
        return self.client.describe(capability_id)

    def _invoke(self, args: Dict[str, Any]) -> Dict[str, Any]:
        capability_id = args.get("capability_id")
        operation = args.get("operation")
        arguments = args.get("arguments") or {}
        if not isinstance(capability_id, str) or not capability_id.strip():
            raise BrokerError("capability_id is required")
        if not isinstance(operation, str) or not operation.strip():
            raise BrokerError("operation is required")
        if not isinstance(arguments, dict):
            raise BrokerError("arguments must be an object")
        return self.client.invoke(capability_id, operation, arguments)

    @staticmethod
    def _reply(output: TextIO, message_id: Any, *, result: Any = None, error: Any = None) -> None:
        response: Dict[str, Any] = {"jsonrpc": "2.0", "id": message_id}
        if error is not None:
            response["error"] = error
        else:
            response["result"] = result
        output.write(json.dumps(response, separators=(",", ":")) + "\n")
        output.flush()

    def serve(self, input_stream: TextIO, output_stream: TextIO) -> None:
        for raw in input_stream:
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            method = message.get("method")
            message_id = message.get("id")
            if method == "initialize":
                self._reply(
                    output_stream,
                    message_id,
                    result={
                        "protocolVersion": message.get("params", {}).get(
                            "protocolVersion", "2024-11-05"
                        ),
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "noldorian", "version": __version__},
                        "instructions": (
                            "List credential capabilities before authenticated work. "
                            "Never inspect vaults or request secret values."
                        ),
                    },
                )
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                self._reply(output_stream, message_id, result={"tools": TOOLS})
            elif method == "tools/call":
                params = message.get("params") or {}
                function = self.dispatch.get(params.get("name"))
                if function is None:
                    self._reply(
                        output_stream,
                        message_id,
                        error={"code": -32602, "message": "unknown tool"},
                    )
                    continue
                try:
                    result = function(params.get("arguments") or {})
                except BrokerError as exc:
                    result = {"error": str(exc)}
                except Exception as exc:  # noqa: BLE001 - fail closed without details
                    result = {"error": f"{type(exc).__name__}: broker request failed"}
                self._reply(
                    output_stream,
                    message_id,
                    result={
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                        "isError": bool(result.get("error")),
                    },
                )
            elif message_id is not None:
                self._reply(
                    output_stream,
                    message_id,
                    error={"code": -32601, "message": "method not supported"},
                )


def main() -> None:
    """Run the Noldorian MCP server over standard input/output."""

    McpServer().serve(sys.stdin, sys.stdout)


if __name__ == "__main__":
    main()
