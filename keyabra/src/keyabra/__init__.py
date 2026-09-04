"""Compatibility re-exports. The documented API is noldorian.vault."""

from noldorian import __version__
from noldorian.vault import (
    LEGACY_ENV_DIR as ENV_DIR,
)
from noldorian.vault import (
    find_dist_files,
    load_env_file,
    load_env_value,
    probe_env_file,
    prompt_secret,
    run_with_env,
)

__all__ = [
    "ENV_DIR",
    "find_dist_files",
    "load_env_file",
    "load_env_value",
    "probe_env_file",
    "prompt_secret",
    "run_with_env",
    "__version__",
]
