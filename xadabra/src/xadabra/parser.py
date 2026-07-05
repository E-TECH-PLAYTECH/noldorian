from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

PLACEHOLDER_RE = re.compile(r"\{\{([^}]+)\}\}")


@dataclass(frozen=True)
class Placeholder:
    name: str
    secret: bool = False
    ptype: str | None = None
    question: str | None = None
    default: str | None = None
    raw: str = ""

    @property
    def prompt_label(self) -> str:
        if self.question:
            return self.question
        return self.name


def parse_placeholder_inner(inner: str) -> Placeholder:
    """Parse the body inside {{ ... }}."""
    raw = inner.strip()
    secret = False
    body = raw
    if body.startswith("!"):
        secret = True
        body = body[1:].strip()

    name_part = body
    rest = ""
    if ":" in body:
        name_part, rest = body.split(":", 1)

    name_part = name_part.strip()
    ptype: str | None = None
    if "|" in name_part:
        name, type_hint = name_part.split("|", 1)
        name = name.strip()
        ptype = type_hint.strip() or None
    else:
        name = name_part.strip()

    question: str | None = None
    default: str | None = None
    if rest:
        if ":" in rest:
            question, default = rest.rsplit(":", 1)
            question = question.strip() or None
            default = default.strip() or None
        else:
            question = rest.strip() or None

    return Placeholder(
        name=name,
        secret=secret,
        ptype=ptype,
        question=question,
        default=default,
        raw=raw,
    )


def find_placeholders(script: str) -> list[Placeholder]:
    """Return placeholders in first-seen order; unique by name."""
    seen: set[str] = set()
    found: list[Placeholder] = []
    for match in PLACEHOLDER_RE.finditer(script):
        ph = parse_placeholder_inner(match.group(1))
        if ph.name not in seen:
            seen.add(ph.name)
            found.append(ph)
    return found


def normalize_path_input(value: str) -> str:
    """Expand ~, strip quotes, unescape macOS drag-and-drop spaces."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    value = value.replace("\\ ", " ")
    return value


def substitute(
    script: str,
    values: dict[str, str],
    *,
    mask_secrets: set[str] | None = None,
) -> str:
    mask_secrets = mask_secrets or set()

    def repl(match: re.Match[str]) -> str:
        ph = parse_placeholder_inner(match.group(1))
        if ph.name not in values:
            return match.group(0)
        val = values[ph.name]
        if ph.secret or ph.name in mask_secrets:
            return "*****"
        return val

    return PLACEHOLDER_RE.sub(repl, script)


def substitute_for_run(script: str, values: dict[str, str]) -> str:
    """Replace placeholders with real values for execution."""

    def repl(match: re.Match[str]) -> str:
        ph = parse_placeholder_inner(match.group(1))
        if ph.name not in values:
            return match.group(0)
        return values[ph.name]

    return PLACEHOLDER_RE.sub(repl, script)


def iter_placeholder_tokens(script: str) -> Iterator[str]:
    for match in PLACEHOLDER_RE.finditer(script):
        yield match.group(0)
