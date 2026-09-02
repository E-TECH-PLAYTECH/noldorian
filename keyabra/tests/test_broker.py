from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from keyabra.broker import (
    BrokerError,
    CapabilityBroker,
    CapabilityStore,
    TunnelAdminAdapter,
)
from keyabra.broker_client import BrokerClient
from keyabra.broker_server import BrokerDaemon


ADMIN_SPEC = {
    "id": "openai.tunnel.admin",
    "provider": "openai",
    "description": "Manage OpenAI Secure MCP Tunnels",
    "adapter": "openai_tunnel_admin",
    "operations": ["tunnels.list", "tunnels.get", "tunnels.create"],
    "resources": {
        "organization_ids": ["org_example"],
        "workspace_ids": ["ws_example"],
    },
}


class CapabilityStoreTests(unittest.TestCase):
    def test_public_catalog_never_contains_secret_or_custody_path(self) -> None:
        secret = b"admin-secret-value-never-returned"
        with tempfile.TemporaryDirectory() as tmp:
            store = CapabilityStore(Path(tmp) / "state")
            store.initialize()
            store.register(ADMIN_SPEC)
            store.enroll("openai.tunnel.admin", secret)

            public = store.list_public()
            encoded = json.dumps(public)
            self.assertNotIn(secret.decode(), encoded)
            self.assertNotIn(".secret", encoded)
            self.assertTrue(public[0]["available"])
            self.assertEqual(store.catalog_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(store._secret_path("openai.tunnel.admin").stat().st_mode & 0o777, 0o600)

    def test_catalog_rejects_secret_fields_and_arbitrary_adapters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = CapabilityStore(Path(tmp) / "state")
            with self.assertRaises(BrokerError):
                store.register({**ADMIN_SPEC, "secret": "must-not-be-catalogued"})
            with self.assertRaises(BrokerError):
                store.register({**ADMIN_SPEC, "adapter": "shell"})
            with self.assertRaises(BrokerError):
                store.register(
                    {
                        **ADMIN_SPEC,
                        "resources": {"api_key": "must-not-be-public-metadata"},
                    }
                )

    def test_legacy_import_is_single_entry_only_and_rejects_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "legacy.env"
            vault.write_text("WANTED=selected-value\nOTHER=must-not-be-copied\n")
            os.chmod(vault, 0o600)
            store = CapabilityStore(root / "state")
            store.register(ADMIN_SPEC)
            result = store.import_env("openai.tunnel.admin", vault, "WANTED")
            self.assertTrue(result["available"])
            self.assertEqual(store.read_secret("openai.tunnel.admin"), b"selected-value")
            self.assertNotIn(b"must-not-be-copied", store.read_secret("openai.tunnel.admin"))

            command_vault = root / "command.env"
            command_vault.write_text("WANTED__CMD=printf should-never-run\n")
            os.chmod(command_vault, 0o600)
            with self.assertRaises(BrokerError):
                store.import_env("openai.tunnel.admin", command_vault, "WANTED")

    def test_unenrolled_capability_is_visible_but_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = CapabilityStore(Path(tmp) / "state")
            described = store.register(ADMIN_SPEC)
            self.assertFalse(described["available"])
            self.assertEqual(described["operations"], sorted(ADMIN_SPEC["operations"]))


class TunnelAdminAdapterTests(unittest.TestCase):
    def test_secret_is_env_only_and_response_is_structurally_redacted(self) -> None:
        secret = b"admin-secret-value-never-returned"
        captured: dict[str, object] = {}

        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured["command"] = list(command)
            child_env = dict(kwargs["env"])  # type: ignore[arg-type]
            captured["env_value"] = child_env["OPENAI_ADMIN_KEY"]
            captured["env_keys"] = sorted(child_env)
            body = {
                "tunnel_id": "tunnel_example",
                "token": secret.decode(),
                "nested": {
                    "message": base64.b64encode(secret).decode(),
                    "authorization": "Bearer " + secret.decode(),
                },
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(body), "")

        adapter = TunnelAdminAdapter("/bin/echo", runner=runner)
        result = adapter.invoke(
            "tunnels.get",
            {"tunnel_id": "tunnel_example"},
            secret,
        )

        self.assertEqual(captured["env_value"], secret.decode())
        self.assertEqual(
            captured["env_keys"],
            ["HOME", "LANG", "OPENAI_ADMIN_KEY", "PATH"],
        )
        self.assertNotIn(secret.decode(), captured["command"])  # type: ignore[operator]
        serialized = json.dumps(result)
        self.assertNotIn(secret.decode(), serialized)
        self.assertNotIn(base64.b64encode(secret).decode(), serialized)
        self.assertIn("[redacted]", serialized)

    def test_invalid_or_unscoped_requests_fail_before_runner(self) -> None:
        calls: list[object] = []

        def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append((args, kwargs))
            raise AssertionError("runner must not be called")

        adapter = TunnelAdminAdapter("/bin/echo", runner=runner)
        with self.assertRaises(BrokerError):
            adapter.invoke("tunnels.list", {}, b"secret")
        with self.assertRaises(BrokerError):
            adapter.invoke("shell", {"command": "env"}, b"secret")
        self.assertEqual(calls, [])


class BrokerSocketTests(unittest.TestCase):
    def test_agent_can_query_but_no_secret_retrieval_action_exists(self) -> None:
        secret = b"socket-secret-value-never-returned"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = CapabilityStore(root / "state")
            store.register(ADMIN_SPEC)
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
            try:
                client = BrokerClient(root / "broker.sock")
                listed = client.list_capabilities()
                self.assertNotIn(secret.decode(), json.dumps(listed))
                self.assertTrue(listed["capabilities"][0]["available"])
                with self.assertRaises(BrokerError):
                    client.request("get_secret", capability_id="openai.tunnel.admin")
            finally:
                daemon.shutdown()
                daemon.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
