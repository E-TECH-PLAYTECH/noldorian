"""Client for the local Noldorian credential capability broker."""

from __future__ import annotations

import json
import os
import socket
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from keyabra.broker import BrokerError


DEFAULT_SOCKET_PATH = Path(
    os.environ.get("NOLDORIAN_BROKER_SOCKET", "/var/run/noldorian-key-broker.sock")
)


class BrokerClient:
    """Small JSON-lines client with no secret retrieval operation."""

    def __init__(self, socket_path: Path = DEFAULT_SOCKET_PATH, *, timeout: float = 120.0) -> None:
        self.socket_path = Path(socket_path)
        self.timeout = timeout

    def request(self, action: str, **params: Any) -> Dict[str, Any]:
        request_id = uuid.uuid4().hex
        payload = {"id": request_id, "action": action, **params}
        encoded = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        if len(encoded) > 1024 * 1024:
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
                    if len(chunks) > 2 * 1024 * 1024:
                        raise BrokerError("broker response exceeds 2 MiB")
        except (FileNotFoundError, ConnectionRefusedError) as exc:
            raise BrokerError(f"Noldorian broker is unavailable at {self.socket_path}") from exc
        except OSError as exc:
            raise BrokerError(f"Noldorian broker request failed: {exc}") from exc

        line = bytes(chunks).split(b"\n", 1)[0]
        try:
            response = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BrokerError("Noldorian broker returned an invalid response") from exc
        if response.get("id") != request_id:
            raise BrokerError("Noldorian broker response id mismatch")
        if not response.get("ok"):
            raise BrokerError(str(response.get("error", "broker request failed")))
        result = response.get("result")
        if not isinstance(result, dict):
            raise BrokerError("Noldorian broker returned a non-object result")
        return result

    def status(self) -> Dict[str, Any]:
        return self.request("status")

    def list_capabilities(self) -> Dict[str, Any]:
        return self.request("list")

    def describe(self, capability_id: str) -> Dict[str, Any]:
        return self.request("describe", capability_id=capability_id)

    def invoke(
        self,
        capability_id: str,
        operation: str,
        arguments: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.request(
            "invoke",
            capability_id=capability_id,
            operation=operation,
            arguments=dict(arguments or {}),
        )
