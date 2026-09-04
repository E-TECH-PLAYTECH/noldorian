from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from keyabra.cli import main

from keyabra import load_env_file, load_env_value, probe_env_file


def write_vault(path: Path, text: str) -> Path:
    path.write_text(text)
    os.chmod(path, 0o600)
    return path


def test_probe_direct_value_returns_metadata_without_secret(tmp_path: Path) -> None:
    secret = "direct-secret-sentinel"
    vault = write_vault(tmp_path / "vault.env", f"TOKEN={secret}\n")

    receipt = probe_env_file(vault, "TOKEN")

    encoded = json.dumps(receipt, sort_keys=True)
    assert receipt["schema"] == "noldorian.env-probe/v1"
    assert receipt["present"] is True
    assert receipt["non_empty"] is True
    assert receipt["mode"] == "0o600"
    assert secret not in encoded


def test_probe_resolves_file_pointer_without_disclosure(tmp_path: Path) -> None:
    secret = "file-secret-sentinel"
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text(secret)
    vault = write_vault(tmp_path / "vault.env", f"TOKEN__FILE={secret_file}\n")

    receipt = probe_env_file(vault, "TOKEN")

    assert receipt["present"] is True
    assert secret not in json.dumps(receipt)


def test_probe_resolves_command_provider_without_disclosure(tmp_path: Path) -> None:
    secret = "command-secret-sentinel"
    vault = write_vault(
        tmp_path / "vault.env",
        f"TOKEN__CMD=printf '{secret}'\n",
    )

    receipt = probe_env_file(vault, "TOKEN")

    assert receipt["non_empty"] is True
    assert secret not in json.dumps(receipt)


def test_probe_does_not_execute_unrelated_provider(tmp_path: Path) -> None:
    vault = write_vault(
        tmp_path / "vault.env",
        "UNRELATED__CMD=exit 7\nTOKEN=target-secret\n",
    )

    receipt = probe_env_file(vault, "TOKEN")

    assert receipt["present"] is True
    assert receipt["non_empty"] is True


def test_selective_load_fails_closed_for_multiple_providers(tmp_path: Path) -> None:
    vault = write_vault(
        tmp_path / "vault.env",
        "TOKEN=direct\nTOKEN__CMD=printf command\n",
    )

    with pytest.raises(ValueError, match="multiple providers"):
        load_env_value(vault, "TOKEN")


def test_probe_fails_closed_for_unsafe_permissions(tmp_path: Path) -> None:
    vault = write_vault(tmp_path / "vault.env", "TOKEN=sentinel\n")
    os.chmod(vault, 0o644)

    with pytest.raises(PermissionError):
        probe_env_file(vault, "TOKEN")


@pytest.mark.parametrize("contents", ["OTHER=value\n", "TOKEN=\n"])
def test_probe_fails_for_missing_or_empty_value(tmp_path: Path, contents: str) -> None:
    vault = write_vault(tmp_path / "vault.env", contents)

    with pytest.raises((KeyError, ValueError)):
        probe_env_file(vault, "TOKEN")


def test_failed_command_does_not_echo_command_stderr(tmp_path: Path) -> None:
    secret = "stderr-secret-sentinel"
    vault = write_vault(
        tmp_path / "vault.env",
        f"TOKEN__CMD=printf '{secret}' >&2; exit 7\n",
    )

    with pytest.raises(RuntimeError) as error:
        load_env_file(vault)

    assert "exit 7" in str(error.value)
    assert secret not in str(error.value)


def test_cli_probe_emits_json_without_secret(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = "cli-secret-sentinel"
    vault = write_vault(tmp_path / "vault.env", f"TOKEN={secret}\n")

    assert main(["env", "probe", "TOKEN", "--file", str(vault)]) == 0

    captured = capsys.readouterr()
    receipt = json.loads(captured.out)
    assert receipt["name"] == "TOKEN"
    assert receipt["present"] is True
    assert secret not in captured.out
    assert secret not in captured.err
