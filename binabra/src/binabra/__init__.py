"""Portable bin-directory anchor for shell scripts."""

from __future__ import annotations

import inspect
import os
from pathlib import Path

__version__ = "0.2.2"


def anchor_dir(path: str | os.PathLike[str] | None = None) -> Path:
    """Directory containing *path*, or the caller's source file when omitted."""
    if path is None:
        frame = inspect.currentframe()
        if frame is None or frame.f_back is None:
            raise RuntimeError("anchor_dir() needs a path or a Python caller frame")
        path = frame.f_back.f_code.co_filename
    return Path(path).resolve().parent


def sibling(name: str, base: str | os.PathLike[str] | None = None) -> Path:
    """Path to a sibling file in the anchored directory."""
    return anchor_dir(base) / name


def anchor_sh_path() -> Path:
    """Path to the bundled anchor.sh shipped with this package."""
    return Path(__file__).resolve().parent / "anchor.sh"


def discover_bin(start: Path | None = None) -> Path | None:
    """Best-effort bin directory: ABRA_BIN, project bin/, then ~/.local/bin."""
    env = os.environ.get("ABRA_BIN")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return p.resolve()

    cwd = (start or Path.cwd()).resolve()
    for directory in [cwd, *cwd.parents]:
        marker = directory / ".abra" / "bin"
        if marker.is_dir():
            return marker.resolve()
        candidate = directory / "bin"
        if candidate.is_dir() and (candidate / "abra").exists():
            return candidate.resolve()
        if directory == Path.home():
            break

    local = Path.home() / ".local" / "bin"
    if local.is_dir():
        return local.resolve()
    return None
