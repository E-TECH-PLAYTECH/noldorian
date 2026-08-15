from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from keyabra.macos_keychain import _codesign_probe, unlock_keychain_from_vault


def write_vault(path: Path, text: str) -> Path:
    path.write_text(text)
    os.chmod(path, 0o600)
    return path


def test_unlock_uses_secret_without_disclosing_it(tmp_path: Path) -> None:
    secret = "login-password-sentinel"
    vault = write_vault(tmp_path / "vault.env", f"LOGIN={secret}\n")
    keychain = tmp_path / "login.keychain-db"
    keychain.touch()
    calls: list[tuple[Path, str]] = []
    probes: list[str] = []

    receipt = unlock_keychain_from_vault(
        vault=vault,
        credential_name="LOGIN",
        keychain=keychain,
        probe_identity="IDENTITY-HASH",
        unlocker=lambda path, password: calls.append((path, password)),
        probe_runner=probes.append,
    )

    assert calls == [(keychain.resolve(), secret)]
    assert probes == ["IDENTITY-HASH"]
    assert receipt["unlocked"] is True
    assert receipt["codesign_probe"]["passed"] is True
    assert secret not in json.dumps(receipt, sort_keys=True)


def test_unlock_without_probe_is_explicit(tmp_path: Path) -> None:
    vault = write_vault(tmp_path / "vault.env", "LOGIN=sentinel\n")
    keychain = tmp_path / "login.keychain-db"
    keychain.touch()

    receipt = unlock_keychain_from_vault(
        vault=vault,
        credential_name="LOGIN",
        keychain=keychain,
        unlocker=lambda _path, _password: None,
    )

    assert receipt["codesign_probe"] == {
        "attempted": False,
        "identity": None,
        "passed": False,
    }


@pytest.mark.parametrize("contents", ["OTHER=value\n", "LOGIN=\n"])
def test_unlock_fails_for_missing_or_empty_secret(
    tmp_path: Path, contents: str
) -> None:
    vault = write_vault(tmp_path / "vault.env", contents)
    keychain = tmp_path / "login.keychain-db"
    keychain.touch()

    with pytest.raises((KeyError, ValueError)):
        unlock_keychain_from_vault(
            vault=vault,
            credential_name="LOGIN",
            keychain=keychain,
            unlocker=lambda _path, _password: None,
        )


def test_probe_failure_does_not_disclose_secret(tmp_path: Path) -> None:
    secret = "probe-failure-sentinel"
    vault = write_vault(tmp_path / "vault.env", f"LOGIN={secret}\n")
    keychain = tmp_path / "login.keychain-db"
    keychain.touch()

    def fail_probe(_identity: str) -> None:
        raise RuntimeError("codesign probe failed")

    with pytest.raises(RuntimeError) as error:
        unlock_keychain_from_vault(
            vault=vault,
            credential_name="LOGIN",
            keychain=keychain,
            probe_identity="IDENTITY-HASH",
            unlocker=lambda _path, _password: None,
            probe_runner=fail_probe,
        )

    assert secret not in str(error.value)


def test_codesign_probe_does_not_copy_sip_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # /usr/bin/true accepts and ignores the codesign-shaped arguments. This
    # exercises creation of the temporary probe without requiring a key.
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/true")

    _codesign_probe("IDENTITY-HASH")
