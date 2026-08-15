"""Non-disclosing macOS keychain enrollment for headless signing jobs."""

from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

from keyabra import load_env_value


class MacOSKeychainError(RuntimeError):
    """A safe-to-display macOS keychain rite failure."""


Unlocker = Callable[[Path, str], None]
ProbeRunner = Callable[[str], None]


def _unlock_with_security_framework(keychain: Path, password: str) -> None:
    """Unlock *keychain* without placing its password in argv or an environment."""
    if sys.platform != "darwin":
        raise MacOSKeychainError("macOS keychain unlock is available only on macOS")

    try:
        security = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/Security.framework/Security"
        )
        core_foundation = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
        )
    except OSError as exc:
        raise MacOSKeychainError("unable to load the macOS Security framework") from exc

    security.SecKeychainOpen.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    security.SecKeychainOpen.restype = ctypes.c_int32
    security.SecKeychainUnlock.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_ubyte,
    ]
    security.SecKeychainUnlock.restype = ctypes.c_int32
    core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
    core_foundation.CFRelease.restype = None

    keychain_ref = ctypes.c_void_p()
    open_status = security.SecKeychainOpen(
        str(keychain).encode("utf-8"), ctypes.byref(keychain_ref)
    )
    if open_status != 0:
        raise MacOSKeychainError(f"SecKeychainOpen failed with OSStatus {open_status}")

    encoded = bytearray(password.encode("utf-8"))
    try:
        password_buffer = (ctypes.c_char * len(encoded)).from_buffer(encoded)
        unlock_status = security.SecKeychainUnlock(
            keychain_ref,
            len(encoded),
            ctypes.cast(password_buffer, ctypes.c_void_p),
            1,
        )
        if unlock_status != 0:
            raise MacOSKeychainError(
                f"SecKeychainUnlock failed with OSStatus {unlock_status}"
            )
    finally:
        for index in range(len(encoded)):
            encoded[index] = 0
        core_foundation.CFRelease(keychain_ref)


def _codesign_probe(identity: str) -> None:
    """Prove that codesign can use *identity* without disclosing secret material."""
    codesign = shutil.which("codesign")
    if not codesign:
        raise MacOSKeychainError("codesign is not available")

    with tempfile.TemporaryDirectory(prefix="keyabra-codesign-") as directory:
        probe = Path(directory) / "probe"
        # ``copy2`` tries to preserve SIP-managed flags and metadata from
        # /usr/bin/true. macOS rejects that metadata write in a temporary
        # directory even though copying the executable contents is allowed.
        shutil.copyfile("/usr/bin/true", probe)
        probe.chmod(0o755)
        completed = subprocess.run(
            [codesign, "--force", "--sign", identity, "--timestamp=none", str(probe)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            raise MacOSKeychainError(
                f"codesign probe failed with exit {completed.returncode}"
            )


def unlock_keychain_from_vault(
    *,
    vault: Path | str,
    credential_name: str,
    keychain: Path | str,
    probe_identity: str | None = None,
    unlocker: Unlocker = _unlock_with_security_framework,
    probe_runner: ProbeRunner = _codesign_probe,
) -> dict[str, object]:
    """Unlock a keychain from a 0600 Keyabra vault and return a redacted receipt."""
    if not credential_name or not credential_name.strip():
        raise ValueError("credential name must not be empty")

    vault_path = Path(vault).expanduser().resolve()
    keychain_path = Path(keychain).expanduser().resolve()
    if not keychain_path.is_file():
        raise FileNotFoundError(f"keychain not found: {keychain_path}")

    password = ""
    try:
        password = load_env_value(vault_path, credential_name)
        if not password:
            raise ValueError(
                f"credential {credential_name!r} resolves to an empty value"
            )

        unlocker(keychain_path, password)
        probe_attempted = probe_identity is not None
        if probe_identity is not None:
            if not probe_identity.strip():
                raise ValueError("codesign probe identity must not be empty")
            probe_runner(probe_identity)

        return {
            "schema": "keyabra.macos-keychain/v1",
            "vault": str(vault_path),
            "credential_name": credential_name,
            "keychain": str(keychain_path),
            "unlocked": True,
            "codesign_probe": {
                "attempted": probe_attempted,
                "identity": probe_identity,
                "passed": probe_attempted,
            },
        }
    finally:
        password = ""
