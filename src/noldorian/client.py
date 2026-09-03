"""Unix-socket client for agent-safe credential capabilities.

The public client intentionally implements no owner, enrollment, credential
retrieval, arbitrary command, or raw HTTP methods.
"""

from __future__ import annotations

import json
import os
import socket
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from noldorian.errors import BrokerError


DEFAULT_SOCKET_PATH = Path(
    os.environ.get("NOLDORIAN_BROKER_SOCKET", "/var/run/noldorian-key-broker.sock")
)
MAX_REQUEST_BYTES = 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class BrokerClient:
    """Query and invoke policy-bound capabilities without accessing secrets."""

    def __init__(
        self,
        socket_path: Path = DEFAULT_SOCKET_PATH,
        *,
        timeout: float = 120.0,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self.socket_path = Path(socket_path)
        self.timeout = timeout

    def _request(self, action: str, **params: Any) -> Dict[str, Any]:
        if action not in {
            "status",
            "list",
            "list_enrollment_templates",
            "describe",
            "invoke",
            "request_enrollment",
            "enrollment_status",
        }:
            raise BrokerError(f"unsupported public broker action: {action}")
        request_id = uuid.uuid4().hex
        payload = {"id": request_id, "action": action, **params}
        encoded = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        if len(encoded) > MAX_REQUEST_BYTES:
            raise BrokerError("broker request exceeds 1 MiB")

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(self.timeout)
                client.connect(str(self.socket_path))
                client.sendall(encoded)
                chunks = bytearray()
                while b"\n" not in chunks:
                    block = client.recv(65536)
                    if not block:
                        break
                    chunks.extend(block)
                    if len(chunks) > MAX_RESPONSE_BYTES:
                        raise BrokerError("broker response exceeds 2 MiB")
        except (FileNotFoundError, ConnectionRefusedError) as exc:
            raise BrokerError(
                f"Noldorian broker is unavailable at {self.socket_path}"
            ) from exc
        except OSError as exc:
            raise BrokerError(f"Noldorian broker request failed: {exc}") from exc

        line = bytes(chunks).split(b"\n", 1)[0]
        try:
            response = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BrokerError("Noldorian broker returned an invalid response") from exc
        if not isinstance(response, dict) or response.get("id") != request_id:
            raise BrokerError("Noldorian broker response id mismatch")
        if not response.get("ok"):
            raise BrokerError(str(response.get("error", "broker request failed")))
        result = response.get("result")
        if not isinstance(result, dict):
            raise BrokerError("Noldorian broker returned a non-object result")
        return result

    def status(self) -> Dict[str, Any]:
        """Return broker readiness and non-secret service metadata."""

        return self._request("status")

    def list_capabilities(self) -> Dict[str, Any]:
        """Return public capability metadata and availability."""

        return self._request("list")

    def list_enrollment_templates(self) -> Dict[str, Any]:
        """Return reviewed enrollment templates without adapter or secret data."""

        return self._request("list_enrollment_templates")

    def describe(self, capability_id: str) -> Dict[str, Any]:
        """Describe one capability without exposing its custody details."""

        if not capability_id.strip():
            raise ValueError("capability_id must not be empty")
        return self._request("describe", capability_id=capability_id)

    def invoke(
        self,
        capability_id: str,
        operation: str,
        arguments: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Invoke one operation already authorized by the owner policy."""

        if not capability_id.strip():
            raise ValueError("capability_id must not be empty")
        if not operation.strip():
            raise ValueError("operation must not be empty")
        return self._request(
            "invoke",
            capability_id=capability_id,
            operation=operation,
            arguments=dict(arguments or {}),
        )

    def request_enrollment(
        self,
        template_id: str,
        purpose: str,
        *,
        capability_id: Optional[str] = None,
        operations: Optional[list[str]] = None,
        resources: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ask the broker to start an owner-only enrollment prompt.

        This method accepts policy metadata only.  It has no parameter for a
        credential value and returns only enrollment status and public data.
        """

        if not template_id.strip():
            raise ValueError("template_id must not be empty")
        if not purpose.strip():
            raise ValueError("purpose must not be empty")
        params: Dict[str, Any] = {"template_id": template_id, "purpose": purpose}
        if capability_id is not None:
            params["capability_id"] = capability_id
        if operations is not None:
            params["operations"] = list(operations)
        if resources is not None:
            params["resources"] = dict(resources)
        return self._request("request_enrollment", **params)

    def enrollment_status(self, request_id: str) -> Dict[str, Any]:
        """Return non-secret status for one owner enrollment request."""

        if not request_id.strip():
            raise ValueError("request_id must not be empty")
        return self._request("enrollment_status", request_id=request_id)
