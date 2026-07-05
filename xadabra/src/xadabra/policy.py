from __future__ import annotations

import re

# Cloud sessions may clone ~/spells for reference but must not cast snx.
_SNX_PATTERNS = (
    re.compile(r"(?:^|[\s;&|])snx\s", re.MULTILINE),
    re.compile(r"python3?\s+-m\s+snax(?:\.cli)?\s", re.MULTILINE),
)


def script_uses_spells(script: str) -> bool:
    return any(p.search(script) for p in _SNX_PATTERNS)
