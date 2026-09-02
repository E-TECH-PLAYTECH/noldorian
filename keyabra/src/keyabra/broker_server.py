"""Root-owned Unix-socket daemon for Noldorian credential capabilities."""

from __future__ import annotations

import argparse
import base64
import ctypes
import json
import os
import socket
import socketserver
import struct
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from keyabra.broker import BrokerError, CapabilityBroker, CapabilityStore


DEFAULT_STATE_DIR = Path("/Library/Application Support/NoldorianKeyBroker")
DEFAULT_SOCKET_PATH = Path("/var/run/noldorian-key-broker.sock")


def _peer_identity(connection: socket.socket) -> Tuple[int, int]:
    """Return peer uid/gid on macOS or Linux without trusting request data."""

    getpeereid = getattr(connection, "getpeereid", None)
    if callable(getpeereid):
        uid, gid = getpeereid()
        return int(uid), int(gid)
    libc = ctypes.CDLL(None, use_errno=True)
    native_getpeereid = getattr(libc, "getpeereid", None)
    if native_getpeereid is not None:
        uid_value = ctypes.c_uint()
        gid_value = ctypes.c_uint()
        native_getpeereid.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_uint),
        ]
        native_getpeereid.restype = ctypes.c_int
        result = native_getpeereid(
            connection.fileno(), ctypes.byref(uid_value), ctypes.byref(gid_value)
        )
        if result == 0:
            return int(uid_value.value), int(gid_value.value)
    if hasattr(socket, "SO_PEERCRED"):
        raw = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        _pid, uid, gid = struct.unpack("3i", raw)
        return int(uid), int(gid)
    raise BrokerError("platform cannot verify Unix-socket peer credentials")


class _ThreadingUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class BrokerRequestHandler(socketserver.StreamRequestHandler):
    """One request per connection; responses never contain credential material."""

    def handle(self) -> None:
        uid, _gid = _peer_identity(self.connection)
        line = self.rfile.readline(1024 * 1024 + 1)
        if len(line) > 1024 * 1024:
            self._write(None, False, error="request exceeds 1 MiB")
            return
        try:
            request = json.loads(line.decode("utf-8"))
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self._write(None, False, error="invalid JSON request")
            return

        request_id = request.get("id")
        try:
            result = self.server.dispatch(uid, request)  # type: ignore[attr-defined]
            self._write(request_id, True, result=result)
        except BrokerError as exc:
            self._write(request_id, False, error=str(exc))
        except Exception as exc:  # noqa: BLE001 - fail closed without daemon exit
            self._write(request_id, False, error=f"broker internal error: {type(exc).__name__}")

    def _write(
        self,
        request_id: Any,
        ok: bool,
        *,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        payload: Dict[str, Any] = {"id": request_id, "ok": ok}
        if ok:
            payload["result"] = result or {}
        else:
            payload["error"] = error or "request failed"
        self.wfile.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))


class BrokerDaemon(_ThreadingUnixServer):
    """Authorized request dispatcher around :class:`CapabilityBroker`."""

    def __init__(
        self,
        socket_path: Path,
        broker: CapabilityBroker,
        *,
        allowed_uids: Set[int],
        owner_uids: Set[int],
        socket_mode: int = 0o660,
        socket_gid: Optional[int] = None,
    ) -> None:
        self.socket_path = Path(socket_path)
        self.broker = broker
        self.allowed_uids = set(allowed_uids) | set(owner_uids)
        self.owner_uids = set(owner_uids)
        self.socket_mode = socket_mode
        self.socket_gid = socket_gid
        if self.socket_path.exists():
            self.socket_path.unlink()
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(str(self.socket_path), BrokerRequestHandler)
        os.chmod(self.socket_path, self.socket_mode)
        if self.socket_gid is not None:
            os.chown(self.socket_path, -1, self.socket_gid)

    def server_close(self) -> None:
        try:
            super().server_close()
        finally:
            if self.socket_path.exists():
                self.socket_path.unlink()

    def _require_allowed(self, uid: int) -> None:
        if uid not in self.allowed_uids:
            raise BrokerError("peer is not authorized to query this broker")

    def _require_owner(self, uid: int) -> None:
        if uid not in self.owner_uids:
            raise BrokerError("owner authorization is required")

    def dispatch(self, uid: int, request: Dict[str, Any]) -> Dict[str, Any]:
        action = request.get("action")
        self._require_allowed(uid)
        if action == "status":
            return {
                "service": "noldorian-key-broker",
                "ready": True,
                "peer_uid": uid,
                "capability_count": len(self.broker.store.list_public()),
            }
        if action == "list":
            return self.broker.list_capabilities()
        if action == "describe":
            return self.broker.describe_capability(str(request.get("capability_id", "")))
        if action == "invoke":
            arguments = request.get("arguments") or {}
            if not isinstance(arguments, dict):
                raise BrokerError("arguments must be an object")
            return self.broker.invoke(
                str(request.get("capability_id", "")),
                str(request.get("operation", "")),
                arguments,
            )

        self._require_owner(uid)
        if action == "register":
            spec = request.get("capability")
            if not isinstance(spec, dict):
                raise BrokerError("capability must be an object")
            return self.broker.store.register(spec)
        if action == "enroll":
            encoded = request.get("secret_b64")
            if not isinstance(encoded, str):
                raise BrokerError("secret_b64 is required")
            try:
                secret = base64.b64decode(encoded, validate=True)
            except ValueError as exc:
                raise BrokerError("secret_b64 is invalid") from exc
            try:
                return self.broker.store.enroll(str(request.get("capability_id", "")), secret)
            finally:
                secret = b""
        if action == "import_env":
            return self.broker.store.import_env(
                str(request.get("capability_id", "")),
                Path(str(request.get("env_file", ""))),
                str(request.get("env_name", "")),
            )
        raise BrokerError(f"unknown broker action: {action}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Noldorian credential capability broker daemon")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--socket", type=Path, default=DEFAULT_SOCKET_PATH)
    parser.add_argument("--tunnel-client-bin", required=True)
    parser.add_argument("--allowed-uid", type=int, action="append", default=[])
    parser.add_argument("--owner-uid", type=int, action="append", default=[0])
    parser.add_argument("--socket-gid", type=int)
    parser.add_argument("--socket-mode", default="0660")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        socket_mode = int(args.socket_mode, 8)
    except ValueError as exc:
        raise SystemExit("--socket-mode must be an octal value such as 0660") from exc
    store = CapabilityStore(args.state_dir)
    store.initialize()
    broker = CapabilityBroker(store, tunnel_client_bin=args.tunnel_client_bin)
    daemon = BrokerDaemon(
        args.socket,
        broker,
        allowed_uids=set(args.allowed_uid),
        owner_uids=set(args.owner_uid),
        socket_mode=socket_mode,
        socket_gid=args.socket_gid,
    )
    try:
        daemon.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        return 0
    finally:
        daemon.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
