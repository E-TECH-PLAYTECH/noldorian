"""Agent-safe credential capability broker core.

The broker deliberately separates three things that legacy Keyabra env-vaults
combined:

* secret custody (root-owned files, never returned by this module),
* public capability metadata (provider, resources, allowed operations), and
* fixed operation adapters (no arbitrary command execution).

The daemon layer in :mod:`keyabra.broker_server` owns the Unix socket and peer
authorization.  This module is transport-independent so its security contract
can be tested without root privileges.
"""

from __future__ import annotations

import base64
import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional
from urllib.parse import quote


CATALOG_SCHEMA = "noldorian.key-capabilities/v1"
CAPABILITY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
TUNNEL_ID_RE = re.compile(r"^tunnel_[A-Za-z0-9]+$")
SENSITIVE_FIELD_RE = re.compile(
    r"(?:secret|token|password|credential|api[_-]?key|authorization)", re.IGNORECASE
)
ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,127}$")
MAX_SECRET_BYTES = 64 * 1024


class BrokerError(RuntimeError):
    """Raised when a capability request violates the broker contract."""


def _chmod_exact(path: Path, mode: int) -> None:
    os.chmod(path, mode)
    actual = path.stat().st_mode & 0o777
    if actual != mode:
        raise BrokerError(f"could not secure {path}: expected {oct(mode)}, got {oct(actual)}")


def _atomic_write(path: Path, payload: bytes, mode: int) -> None:
    """Atomically write *payload* beside *path* with an exact permission mode."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        _chmod_exact(tmp, mode)
        os.replace(tmp, path)
        _chmod_exact(path, mode)
    finally:
        if tmp.exists():
            tmp.unlink()


def _secret_variants(secret: str) -> List[str]:
    raw = secret.encode("utf-8")
    variants = {
        secret,
        base64.b64encode(raw).decode("ascii"),
        base64.urlsafe_b64encode(raw).decode("ascii"),
        raw.hex(),
        quote(secret, safe=""),
    }
    return sorted((value for value in variants if value), key=len, reverse=True)


def _sanitize(value: Any, secret: str) -> Any:
    """Remove direct and common encoded secret representations recursively."""

    variants = _secret_variants(secret)

    def clean(item: Any, field_name: str = "") -> Any:
        if field_name and SENSITIVE_FIELD_RE.search(field_name):
            return "[redacted]"
        if isinstance(item, str):
            result = item
            for variant in variants:
                result = result.replace(variant, "[redacted]")
            return result
        if isinstance(item, list):
            return [clean(child) for child in item]
        if isinstance(item, dict):
            return {str(key): clean(child, str(key)) for key, child in item.items()}
        return item

    return clean(value)


def _validate_public_metadata(value: Any, path: str = "resources") -> None:
    """Reject metadata shapes that could accidentally publish credential fields."""

    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or not key.strip():
                raise BrokerError(f"{path} keys must be non-empty strings")
            if SENSITIVE_FIELD_RE.search(key):
                raise BrokerError(f"{path}.{key} looks like credential material")
            _validate_public_metadata(child, f"{path}.{key}")
        return
    if isinstance(value, list):
        if len(value) > 256:
            raise BrokerError(f"{path} contains too many entries")
        for index, child in enumerate(value):
            _validate_public_metadata(child, f"{path}[{index}]")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, str) and len(value) <= 1000:
        return
    raise BrokerError(f"{path} must contain bounded JSON metadata")


def _require_text(args: Mapping[str, Any], name: str, *, max_length: int = 500) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise BrokerError(f"{name} must be a non-empty string")
    value = value.strip()
    if len(value) > max_length:
        raise BrokerError(f"{name} exceeds {max_length} characters")
    return value


def _string_list(args: Mapping[str, Any], name: str) -> List[str]:
    value = args.get(name, [])
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise BrokerError(f"{name} must be a string or list of strings")
    cleaned = [item.strip() for item in value if item.strip()]
    if len(cleaned) != len(set(cleaned)):
        raise BrokerError(f"{name} contains duplicates")
    return cleaned


class TunnelAdminAdapter:
    """Fixed OpenAI Secure MCP Tunnel admin operations.

    No command or flag is accepted from the capability catalog.  Agent input is
    parsed into a small typed argument set and translated to native
    ``tunnel-client admin tunnels`` commands without a shell.
    """

    OPERATIONS = frozenset({"tunnels.list", "tunnels.get", "tunnels.create"})

    def __init__(
        self,
        tunnel_client_bin: str,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        binary = Path(tunnel_client_bin).expanduser()
        if not binary.is_absolute():
            raise BrokerError("tunnel-client binary must be an absolute path")
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise BrokerError(f"tunnel-client binary is not executable: {binary}")
        binary_stat = binary.stat()
        if binary_stat.st_uid != 0 or binary_stat.st_mode & 0o022:
            raise BrokerError("tunnel-client binary must be root-owned and not group/other-writable")
        self._binary = str(binary)
        self._runner = runner

    def _build_command(self, operation: str, args: Mapping[str, Any]) -> List[str]:
        if operation not in self.OPERATIONS:
            raise BrokerError(f"unsupported tunnel admin operation: {operation}")

        verb = operation.split(".", 1)[1]
        command = [self._binary, "admin", "--json", "tunnels", verb]

        if operation == "tunnels.get":
            tunnel_id = _require_text(args, "tunnel_id", max_length=128)
            if not TUNNEL_ID_RE.fullmatch(tunnel_id):
                raise BrokerError("tunnel_id has an invalid shape")
            command.append(tunnel_id)
            return command

        organization_ids = _string_list(args, "organization_ids")
        workspace_ids = _string_list(args, "workspace_ids")

        if operation == "tunnels.list":
            tenant_id = args.get("tenant_id")
            if tenant_id is not None and (not isinstance(tenant_id, str) or not tenant_id.strip()):
                raise BrokerError("tenant_id must be a non-empty string")
            scope_count = int(bool(organization_ids)) + int(bool(workspace_ids)) + int(bool(tenant_id))
            if scope_count != 1:
                raise BrokerError(
                    "tunnels.list requires exactly one scope: organization_ids, "
                    "workspace_ids, or tenant_id"
                )
            if tenant_id:
                command.extend(["--tenant-id", tenant_id.strip()])
        else:
            name = _require_text(args, "name", max_length=160)
            description = _require_text(args, "description", max_length=1000)
            if not organization_ids and not workspace_ids:
                raise BrokerError("tunnels.create requires an organization or workspace scope")
            command.extend(["--name", name, "--description", description])

        for organization_id in organization_ids:
            command.extend(["--organization-id", organization_id])
        for workspace_id in workspace_ids:
            command.extend(["--workspace-id", workspace_id])
        return command

    def invoke(self, operation: str, args: Mapping[str, Any], secret: bytes) -> Dict[str, Any]:
        try:
            secret_text = secret.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise BrokerError("credential is not UTF-8 text") from exc
        if not secret_text:
            raise BrokerError("credential is empty")

        command = self._build_command(operation, args)
        child_env = {
            "HOME": "/var/empty",
            "LANG": "C.UTF-8",
            "OPENAI_ADMIN_KEY": secret_text,
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        }
        try:
            completed = self._runner(
                command,
                capture_output=True,
                text=True,
                env=child_env,
                timeout=90,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise BrokerError("tunnel-client operation timed out") from exc
        finally:
            child_env["OPENAI_ADMIN_KEY"] = ""

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        parsed: Any
        try:
            parsed = json.loads(stdout) if stdout.strip() else None
        except json.JSONDecodeError:
            parsed = {"message": stdout[-4000:]}

        result = {
            "ok": completed.returncode == 0,
            "operation": operation,
            "exit_code": completed.returncode,
            "result": parsed,
            "stderr": stderr[-2000:],
        }
        return _sanitize(result, secret_text)


class CapabilityStore:
    """Root-owned capability catalog and secret custody store."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = Path(state_dir).expanduser().resolve()
        self.catalog_path = self.state_dir / "capabilities.json"
        self.secrets_dir = self.state_dir / "secrets"

    def initialize(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.secrets_dir.mkdir(parents=True, exist_ok=True)
        _chmod_exact(self.state_dir, 0o700)
        _chmod_exact(self.secrets_dir, 0o700)
        if not self.catalog_path.exists():
            self._write_catalog({"schema": CATALOG_SCHEMA, "capabilities": {}})
        else:
            _chmod_exact(self.catalog_path, 0o600)

    def _load_catalog(self) -> MutableMapping[str, Any]:
        self.initialize()
        try:
            catalog = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BrokerError("capability catalog is unreadable or invalid") from exc
        if catalog.get("schema") != CATALOG_SCHEMA or not isinstance(catalog.get("capabilities"), dict):
            raise BrokerError("capability catalog has an unsupported schema")
        return catalog

    def _write_catalog(self, catalog: Mapping[str, Any]) -> None:
        payload = (json.dumps(catalog, indent=2, sort_keys=True) + "\n").encode("utf-8")
        _atomic_write(self.catalog_path, payload, 0o600)

    @staticmethod
    def _validate_spec(spec: Mapping[str, Any]) -> Dict[str, Any]:
        allowed_fields = {
            "id",
            "provider",
            "description",
            "adapter",
            "operations",
            "resources",
            "owner_note",
        }
        unknown = sorted(set(spec) - allowed_fields)
        if unknown:
            raise BrokerError(f"unsupported capability fields: {', '.join(unknown)}")

        capability_id = spec.get("id")
        if not isinstance(capability_id, str) or not CAPABILITY_ID_RE.fullmatch(capability_id):
            raise BrokerError("capability id must use lowercase letters, digits, dots, dashes, or underscores")
        provider = spec.get("provider")
        description = spec.get("description")
        adapter = spec.get("adapter")
        operations = spec.get("operations", [])
        resources = spec.get("resources", {})
        if not isinstance(provider, str) or not provider.strip():
            raise BrokerError("provider must be a non-empty string")
        if not isinstance(description, str) or not description.strip():
            raise BrokerError("description must be a non-empty string")
        if adapter not in {"presence", "openai_tunnel_admin"}:
            raise BrokerError("adapter must be presence or openai_tunnel_admin")
        if not isinstance(operations, list) or any(not isinstance(item, str) for item in operations):
            raise BrokerError("operations must be a list of strings")
        if adapter == "presence" and operations:
            raise BrokerError("presence capabilities cannot expose operations")
        if adapter == "openai_tunnel_admin" and not set(operations).issubset(TunnelAdminAdapter.OPERATIONS):
            raise BrokerError("capability requests an unsupported tunnel admin operation")
        if len(operations) != len(set(operations)):
            raise BrokerError("operations contains duplicates")
        if not isinstance(resources, dict):
            raise BrokerError("resources must be an object")
        _validate_public_metadata(resources)

        return {
            "id": capability_id,
            "provider": provider.strip(),
            "description": description.strip(),
            "adapter": adapter,
            "operations": sorted(operations),
            "resources": resources,
            "owner_note": str(spec.get("owner_note", "")).strip(),
        }

    def register(self, spec: Mapping[str, Any]) -> Dict[str, Any]:
        clean = self._validate_spec(spec)
        catalog = self._load_catalog()
        catalog["capabilities"][clean["id"]] = clean
        self._write_catalog(catalog)
        return self.describe(clean["id"])

    def _secret_path(self, capability_id: str) -> Path:
        if not CAPABILITY_ID_RE.fullmatch(capability_id):
            raise BrokerError("invalid capability id")
        return self.secrets_dir / f"{capability_id}.secret"

    def enroll(self, capability_id: str, secret: bytes) -> Dict[str, Any]:
        self._get_spec(capability_id)
        if not isinstance(secret, bytes) or not secret.strip():
            raise BrokerError("secret must be non-empty bytes")
        _atomic_write(self._secret_path(capability_id), secret.strip() + b"\n", 0o600)
        return self.describe(capability_id)

    def import_env(self, capability_id: str, env_file: Path, env_name: str) -> Dict[str, Any]:
        """Import exactly one legacy value without executing vault commands.

        Legacy ``NAME__CMD`` entries are intentionally forbidden here: this
        method runs in the root broker and must never execute text from a
        user-writable vault.  ``NAME`` and ``NAME__FILE`` are copied once into
        root custody; subsequent agent operations never revisit the vault.
        """

        if not ENV_NAME_RE.fullmatch(env_name):
            raise BrokerError("env_name must be an uppercase environment variable name")
        vault_path = Path(env_file).expanduser().resolve()
        if not vault_path.is_file():
            raise BrokerError("legacy vault file does not exist")
        vault_stat = vault_path.stat()
        if vault_stat.st_mode & 0o077:
            raise BrokerError("legacy vault must not be group/other-accessible")

        matches: Dict[str, str] = {}
        try:
            with vault_path.open("r", encoding="utf-8") as handle:
                for raw in handle:
                    if len(raw.encode("utf-8")) > MAX_SECRET_BYTES:
                        raise BrokerError("legacy vault contains an oversized line")
                    line = raw.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    name, _, value = line.partition("=")
                    name = name.strip()
                    if name not in {env_name, f"{env_name}__FILE", f"{env_name}__CMD"}:
                        continue
                    if name in matches:
                        raise BrokerError(f"legacy vault contains duplicate entry {name}")
                    value = value.strip()
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                        value = value[1:-1]
                    matches[name] = value
        except UnicodeDecodeError as exc:
            raise BrokerError("legacy vault is not UTF-8 text") from exc

        if f"{env_name}__CMD" in matches:
            raise BrokerError("legacy __CMD entries cannot be imported into the root broker")
        selected = [name for name in (env_name, f"{env_name}__FILE") if name in matches]
        if not selected:
            raise BrokerError(f"legacy vault has no entry named {env_name}")
        if len(selected) != 1:
            raise BrokerError(f"legacy vault has conflicting entries for {env_name}")

        selected_name = selected[0]
        if selected_name.endswith("__FILE"):
            target = Path(matches[selected_name]).expanduser().resolve()
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            try:
                fd = os.open(target, flags)
            except OSError as exc:
                raise BrokerError("legacy secret pointer cannot be opened safely") from exc
            try:
                target_stat = os.fstat(fd)
                if not stat.S_ISREG(target_stat.st_mode):
                    raise BrokerError("legacy secret pointer must target a regular file")
                if target_stat.st_mode & 0o077:
                    raise BrokerError("legacy secret pointer must not be group/other-accessible")
                value = os.read(fd, MAX_SECRET_BYTES + 1)
            finally:
                os.close(fd)
        else:
            value = matches[selected_name].encode("utf-8")
        if len(value) > MAX_SECRET_BYTES:
            raise BrokerError("legacy credential exceeds 64 KiB")
        try:
            return self.enroll(capability_id, value)
        finally:
            matches.clear()
            value = b""

    def _get_spec(self, capability_id: str) -> Mapping[str, Any]:
        catalog = self._load_catalog()
        spec = catalog["capabilities"].get(capability_id)
        if not isinstance(spec, dict):
            raise BrokerError(f"unknown capability: {capability_id}")
        return spec

    def _public(self, spec: Mapping[str, Any]) -> Dict[str, Any]:
        capability_id = str(spec["id"])
        return {
            "id": capability_id,
            "provider": spec["provider"],
            "description": spec["description"],
            "operations": list(spec.get("operations", [])),
            "resources": spec.get("resources", {}),
            "available": self._secret_path(capability_id).is_file(),
        }

    def list_public(self) -> List[Dict[str, Any]]:
        catalog = self._load_catalog()
        return [
            self._public(catalog["capabilities"][capability_id])
            for capability_id in sorted(catalog["capabilities"])
        ]

    def describe(self, capability_id: str) -> Dict[str, Any]:
        return self._public(self._get_spec(capability_id))

    def read_secret(self, capability_id: str) -> bytes:
        path = self._secret_path(capability_id)
        if not path.is_file():
            raise BrokerError(f"capability is not enrolled: {capability_id}")
        if path.stat().st_mode & 0o077:
            raise BrokerError("credential custody file has unsafe permissions")
        secret = path.read_bytes().strip()
        if not secret:
            raise BrokerError("credential custody file is empty")
        return secret


class CapabilityBroker:
    """Public capability query/invocation facade used by the daemon."""

    def __init__(self, store: CapabilityStore, *, tunnel_client_bin: str) -> None:
        self.store = store
        self._adapters = {
            "openai_tunnel_admin": TunnelAdminAdapter(tunnel_client_bin),
        }

    def list_capabilities(self) -> Dict[str, Any]:
        return {"schema": CATALOG_SCHEMA, "capabilities": self.store.list_public()}

    def describe_capability(self, capability_id: str) -> Dict[str, Any]:
        return self.store.describe(capability_id)

    def invoke(
        self,
        capability_id: str,
        operation: str,
        arguments: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        spec = self.store._get_spec(capability_id)
        allowed = set(spec.get("operations", []))
        if operation not in allowed:
            raise BrokerError(f"operation is not allowed for {capability_id}: {operation}")
        adapter_name = str(spec.get("adapter"))
        adapter = self._adapters.get(adapter_name)
        if adapter is None:
            raise BrokerError(f"capability has no invocable adapter: {capability_id}")
        secret = self.store.read_secret(capability_id)
        try:
            result = adapter.invoke(operation, arguments or {}, secret)
        finally:
            secret = b""
        return {
            "capability_id": capability_id,
            "provider": spec["provider"],
            **result,
        }
