"""Zero-dependency MCP server for public Noldorian operations."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TextIO

from noldorian import __version__
from noldorian.client import BrokerClient, DEFAULT_SOCKET_PATH
from noldorian.doctor import doctor_report
from noldorian.errors import BrokerError
from noldorian.vault import (
    child_run_template,
    default_vault_path,
    list_vault_names,
)

ALWAYS_TOOLS = [
    {
        "name": "doctor",
        "description": (
            "Report whether Noldorian is installed, the vault contract path, "
            "and whether the optional Gondolin socket is present. Never returns "
            "credentials."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "orient",
        "description": "How to install Noldorian and use the vault on this machine.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "enum": ["deploy", "bootstrap", "owner-actions", "all"],
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "list_vault_names",
        "description": (
            "List logical names in the local 0600 vault. Returns names only, "
            "never values. Empty if no vault is present."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "child_run_template",
        "description": (
            "Return the owner-run command template that loads the vault into a "
            "child process. Does not execute the command or return secrets."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "additionalProperties": False,
        },
    },
]

EXTENSION_TOOLS = [
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
        "name": "list_credential_enrollment_templates",
        "description": (
            "List reviewed credential enrollment templates, supported operations, and "
            "providers without returning credential values or custody data."
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
    {
        "name": "request_credential_enrollment",
        "description": (
            "Ask Noldorian to open the owner-only human enrollment prompt for a reviewed "
            "template. This accepts policy metadata only, never a credential value, and "
            "returns non-secret status. Poll the request with get_credential_enrollment_status."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "template_id": {"type": "string", "minLength": 1},
                "purpose": {"type": "string", "minLength": 1, "maxLength": 500},
                "capability_id": {"type": "string", "minLength": 3, "maxLength": 128},
                "operations": {"type": "array", "items": {"type": "string"}},
                "resources": {"type": "object"},
            },
            "required": ["template_id", "purpose"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_credential_enrollment_status",
        "description": "Return non-secret status for one Noldorian human enrollment request.",
        "inputSchema": {
            "type": "object",
            "properties": {"request_id": {"type": "string", "minLength": 1}},
            "required": ["request_id"],
            "additionalProperties": False,
        },
    },
]

TOOLS = ALWAYS_TOOLS + EXTENSION_TOOLS


def _orient(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import xalakazam
    except ImportError:
        return {"error": "xalakazam surface is unavailable"}
    topic = (args or {}).get("topic") or "deploy"
    docs = {
        "deploy": xalakazam.DEPLOY,
        "bootstrap": xalakazam.BOOTSTRAP_HINT,
        "owner-actions": xalakazam.OWNER_ACTIONS,
    }
    if topic == "all":
        return {"text": "\n\n".join(docs.values())}
    if topic not in docs:
        return {"error": f"unknown topic {topic!r}"}
    return {"text": docs[topic]}


def _list_vault_names(_args: Dict[str, Any]) -> Dict[str, Any]:
    vault = default_vault_path()
    if not vault.is_file():
        return {"vault": str(vault), "present": False, "names": []}
    try:
        names = list_vault_names(vault)
    except (OSError, ValueError, PermissionError) as exc:
        return {"vault": str(vault), "present": True, "names": [], "error": str(exc)}
    return {"vault": str(vault), "present": True, "names": names}


def _child_run_template(args: Dict[str, Any]) -> Dict[str, Any]:
    command = args.get("command") if isinstance(args.get("command"), str) else "<command>"
    return child_run_template(command)


class McpServer:
    """JSON-RPC loop: vault/doctor always; Gondolin tools if the client is used."""

    def __init__(self, client: Optional[BrokerClient] = None) -> None:
        self.client = client or BrokerClient(DEFAULT_SOCKET_PATH)
        self.dispatch: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            "doctor": lambda _args: doctor_report(),
            "orient": _orient,
            "list_vault_names": _list_vault_names,
            "child_run_template": _child_run_template,
            "broker_status": lambda _args: self.client.status(),
            "list_credential_capabilities": lambda _args: self.client.list_capabilities(),
            "list_credential_enrollment_templates": lambda _args: self.client.list_enrollment_templates(),
            "describe_credential_capability": self._describe,
            "invoke_credential_capability": self._invoke,
            "request_credential_enrollment": self._request_enrollment,
            "get_credential_enrollment_status": self._enrollment_status,
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

    def _request_enrollment(self, args: Dict[str, Any]) -> Dict[str, Any]:
        template_id = args.get("template_id")
        purpose = args.get("purpose")
        if not isinstance(template_id, str) or not template_id.strip():
            raise BrokerError("template_id is required")
        if not isinstance(purpose, str) or not purpose.strip():
            raise BrokerError("purpose is required")
        capability_id = args.get("capability_id")
        operations = args.get("operations")
        resources = args.get("resources")
        if capability_id is not None and not isinstance(capability_id, str):
            raise BrokerError("capability_id must be a string")
        if operations is not None and (
            not isinstance(operations, list) or any(not isinstance(item, str) for item in operations)
        ):
            raise BrokerError("operations must be an array of strings")
        if resources is not None and not isinstance(resources, dict):
            raise BrokerError("resources must be an object")
        return self.client.request_enrollment(
            template_id,
            purpose,
            capability_id=capability_id,
            operations=operations,
            resources=resources,
        )

    def _enrollment_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request_id = args.get("request_id")
        if not isinstance(request_id, str) or not request_id.strip():
            raise BrokerError("request_id is required")
        return self.client.enrollment_status(request_id)

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
                            "Call doctor first. Everyday credential use is the owner-run "
                            "vault: list_vault_names then child_run_template. Never request "
                            "secret values. Gondolin broker tools are optional and fail "
                            "with extension absent when no socket is present."
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

    from noldorian.vault import ensure_canonical_home

    ensure_canonical_home()
    McpServer().serve(sys.stdin, sys.stdout)


if __name__ == "__main__":
    main()
