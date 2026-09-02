#!/usr/bin/env python3
"""Read-only discovery and policy-bound invocation for Noldorian credentials.

This MCP server intentionally has no enrollment, export, clipboard, shell, or
secret-value tool.  It is a thin client of the root-owned Keyabra broker.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict


def _load_client() -> tuple[type, type]:
    try:
        from keyabra.broker import BrokerError
        from keyabra.broker_client import BrokerClient

        return BrokerClient, BrokerError
    except ImportError:
        repo_src = Path(__file__).resolve().parent.parent / "keyabra" / "src"
        sys.path.insert(0, str(repo_src))
        from keyabra.broker import BrokerError
        from keyabra.broker_client import BrokerClient

        return BrokerClient, BrokerError


BrokerClient, BrokerError = _load_client()
SOCKET_PATH = Path(
    os.environ.get("NOLDORIAN_BROKER_SOCKET", "/var/run/noldorian-key-broker.sock")
)


def _client() -> Any:
    return BrokerClient(SOCKET_PATH)


def tool_broker_status(_args: Dict[str, Any]) -> Dict[str, Any]:
    return _client().status()


def tool_list_capabilities(_args: Dict[str, Any]) -> Dict[str, Any]:
    return _client().list_capabilities()


def tool_describe_capability(args: Dict[str, Any]) -> Dict[str, Any]:
    capability_id = args.get("capability_id")
    if not isinstance(capability_id, str) or not capability_id:
        return {"error": "capability_id is required"}
    return _client().describe(capability_id)


def tool_invoke_capability(args: Dict[str, Any]) -> Dict[str, Any]:
    capability_id = args.get("capability_id")
    operation = args.get("operation")
    arguments = args.get("arguments") or {}
    if not isinstance(capability_id, str) or not capability_id:
        return {"error": "capability_id is required"}
    if not isinstance(operation, str) or not operation:
        return {"error": "operation is required"}
    if not isinstance(arguments, dict):
        return {"error": "arguments must be an object"}
    return _client().invoke(capability_id, operation, arguments)


TOOLS = [
    {
        "name": "broker_status",
        "description": "Check whether the local Noldorian credential capability broker is ready.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_credential_capabilities",
        "description": (
            "List credential capabilities, providers, approved operations, resources, and "
            "availability. Secret values and custody paths are never returned."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "describe_credential_capability",
        "description": "Describe one credential capability without returning its secret or storage path.",
        "inputSchema": {
            "type": "object",
            "properties": {"capability_id": {"type": "string"}},
            "required": ["capability_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "invoke_credential_capability",
        "description": (
            "Invoke one operation explicitly approved for a capability. The broker injects the "
            "credential internally and structurally sanitizes the result. Arbitrary commands are "
            "not accepted."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "capability_id": {"type": "string"},
                "operation": {"type": "string"},
                "arguments": {"type": "object"},
            },
            "required": ["capability_id", "operation"],
            "additionalProperties": False,
        },
    },
]


DISPATCH: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "broker_status": tool_broker_status,
    "list_credential_capabilities": tool_list_capabilities,
    "describe_credential_capability": tool_describe_capability,
    "invoke_credential_capability": tool_invoke_capability,
}


def _reply(message_id: Any, *, result: Any = None, error: Any = None) -> None:
    response: Dict[str, Any] = {"jsonrpc": "2.0", "id": message_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
    sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main() -> None:
    for raw in sys.stdin:
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            continue
        method = message.get("method")
        message_id = message.get("id")
        if method == "initialize":
            _reply(
                message_id,
                result={
                    "protocolVersion": message.get("params", {}).get(
                        "protocolVersion", "2024-11-05"
                    ),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "noldorian-capabilities", "version": "0.1.0"},
                    "instructions": (
                        "Query credential capabilities before attempting authenticated work. "
                        "Never inspect vaults or request secret values. Invoke only operations "
                        "listed by list_credential_capabilities."
                    ),
                },
            )
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            _reply(message_id, result={"tools": TOOLS})
        elif method == "tools/call":
            params = message.get("params") or {}
            name = params.get("name")
            function = DISPATCH.get(name)
            if function is None:
                _reply(
                    message_id,
                    error={"code": -32602, "message": f"unknown tool {name!r}"},
                )
                continue
            try:
                result = function(params.get("arguments") or {})
            except BrokerError as exc:
                result = {"error": str(exc)}
            except Exception as exc:  # noqa: BLE001 - fail closed without server exit
                result = {"error": f"{type(exc).__name__}: broker request failed"}
            _reply(
                message_id,
                result={
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                    "isError": bool(isinstance(result, dict) and result.get("error")),
                },
            )
        elif message_id is not None:
            _reply(
                message_id,
                error={"code": -32601, "message": f"method {method!r} not supported"},
            )


if __name__ == "__main__":
    main()
