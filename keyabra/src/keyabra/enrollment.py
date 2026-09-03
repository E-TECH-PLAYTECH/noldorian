"""Human-gated enrollment orchestration for the Noldorian broker.

The agent can request a reviewed capability template, but it cannot submit a
credential and cannot choose an adapter.  The broker launches the owner prompt
as a separate desktop-user process and receives its answer over a private
parent/child pipe.  Only the broker writes the credential into root custody.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Callable, Dict, Mapping, Optional

from keyabra.broker import BrokerError, CapabilityStore, MAX_SECRET_BYTES


class EnrollmentCancelled(BrokerError):
    """The human explicitly dismissed the enrollment prompt."""


class HumanEnrollmentGate:
    """Launch the owner-only prompt without putting a secret on agent surfaces."""

    def __init__(
        self,
        *,
        prompt_uid: Optional[int],
        prompt_python: Optional[str],
        prompt_app: Optional[str],
        launchctl_bin: str = "/bin/launchctl",
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.prompt_uid = prompt_uid
        self.prompt_python = prompt_python
        self.prompt_app = prompt_app
        self.launchctl_bin = launchctl_bin
        self._runner = runner

    def _validate_configuration(self) -> None:
        if self.prompt_uid is None or not self.prompt_python or not self.prompt_app:
            raise BrokerError("human enrollment prompt is not configured")
        for value, label in (
            (self.prompt_python, "prompt Python"),
            (self.prompt_app, "prompt application"),
            (self.launchctl_bin, "launchctl"),
        ):
            path = Path(value)
            if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
                raise BrokerError(f"{label} is not executable")

    def collect(self, request: Mapping[str, Any]) -> bytes:
        self._validate_configuration()
        command = [
            self.launchctl_bin,
            "asuser",
            str(self.prompt_uid),
            str(self.prompt_python),
            str(self.prompt_app),
            "--owner-prompt",
        ]
        request_json = json.dumps(
            {
                "capability_id": request["capability_id"],
                "provider": request["provider"],
                "description": request["description"],
                "operations": request["operations"],
                "resources": request["resources"],
                "purpose": request["purpose"],
            },
            separators=(",", ":"),
            ensure_ascii=False,
        )
        try:
            completed = self._runner(
                command,
                input=request_json + "\n",
                capture_output=True,
                text=True,
                env={"LANG": "C.UTF-8", "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
                timeout=300,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise BrokerError("human enrollment prompt timed out") from exc
        except OSError as exc:
            raise BrokerError("human enrollment prompt could not be started") from exc

        stdout = completed.stdout or ""
        # Do not include stdout/stderr in an error.  stdout is the private pipe
        # that may contain the one-time response from the owner UI.
        try:
            if completed.returncode != 0:
                raise BrokerError("human enrollment prompt failed")
            lines = [line.strip() for line in stdout.splitlines() if line.strip()]
            if not lines:
                raise BrokerError("human enrollment prompt returned no decision")
            response = json.loads(lines[-1])
            if not isinstance(response, dict):
                raise BrokerError("human enrollment prompt returned an invalid decision")
            if response.get("status") == "cancelled":
                raise EnrollmentCancelled("human enrollment was cancelled")
            if response.get("status") != "approved":
                raise BrokerError("human enrollment prompt did not approve the request")
            encoded = response.get("secret_b64")
            if not isinstance(encoded, str):
                raise BrokerError("human enrollment prompt returned no credential")
            try:
                secret = base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError) as exc:
                raise BrokerError("human enrollment prompt returned an invalid credential") from exc
            if not secret or len(secret) > MAX_SECRET_BYTES:
                raise BrokerError("human enrollment credential is empty or oversized")
            return secret
        finally:
            # Drop the private response as soon as it has been decoded.  The
            # agent-facing result never receives this object or its encoding.
            stdout = ""
            completed.stdout = ""
            completed.stderr = ""


class EnrollmentCoordinator:
    """Create idempotent enrollment requests and complete them in the broker."""

    def __init__(self, store: CapabilityStore, gate: HumanEnrollmentGate) -> None:
        self.store = store
        self.gate = gate
        self._lock = Lock()
        self._active: set[str] = set()

    def request(self, args: Mapping[str, Any]) -> Dict[str, Any]:
        with self._lock:
            prepared = self.store.prepare_enrollment(args)
            capability_id = str(prepared["capability_id"])

            try:
                existing = self.store.describe(capability_id)
            except BrokerError:
                existing = None
            if existing and existing.get("available"):
                return {
                    "schema": prepared["schema"],
                    "request_id": None,
                    "capability_id": capability_id,
                    "provider": prepared["provider"],
                    "status": "already_available",
                    "capability": existing,
                }

            open_request = self.store.find_open_enrollment(capability_id)
            if open_request:
                return self.store.enrollment_status(str(open_request["request_id"]))

            self.store.create_enrollment(prepared)
            request_id = str(prepared["request_id"])
            self._active.add(request_id)
        Thread(target=self._complete, args=(request_id,), daemon=True).start()
        return self.store.enrollment_status(request_id)

    def _complete(self, request_id: str) -> None:
        secret = b""
        try:
            self.store.update_enrollment(request_id, "prompt_opened")
            request = self.store._load_enrollment(request_id)
            self.store.update_enrollment(request_id, "prompting")
            secret = self.gate.collect(request)
            spec = request.get("spec")
            if not isinstance(spec, dict):
                raise BrokerError("enrollment request has no capability specification")
            self.store.register(spec)
            self.store.enroll(str(request["capability_id"]), secret)
            self.store.update_enrollment(request_id, "enrolled")
        except EnrollmentCancelled:
            self.store.update_enrollment(request_id, "cancelled", error_code="human_cancelled")
        except BrokerError as exc:
            error_code = "prompt_unavailable" if "prompt" in str(exc) else "enrollment_failed"
            self.store.update_enrollment(request_id, "failed", error_code=error_code)
        except Exception:  # noqa: BLE001 - fail closed without leaking details
            self.store.update_enrollment(request_id, "failed", error_code="enrollment_failed")
        finally:
            secret = b""
            with self._lock:
                self._active.discard(request_id)
