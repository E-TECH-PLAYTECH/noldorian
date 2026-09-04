"""Public Noldorian surfaces: vault contract, optional extension client, MCP."""

from noldorian.client import BrokerClient, DEFAULT_SOCKET_PATH
from noldorian.errors import BrokerError
from noldorian.vault import (
    ENV_DIR,
    LEGACY_ENV_DIR,
    child_run_template,
    default_vault_path,
    list_vault_names,
    load_env_file,
    load_env_value,
    probe_env_file,
    prompt_secret,
    run_with_env,
)

__all__ = [
    "BrokerClient",
    "BrokerError",
    "DEFAULT_SOCKET_PATH",
    "ENV_DIR",
    "LEGACY_ENV_DIR",
    "child_run_template",
    "default_vault_path",
    "list_vault_names",
    "load_env_file",
    "load_env_value",
    "probe_env_file",
    "prompt_secret",
    "run_with_env",
]
__version__ = "0.2.1"
