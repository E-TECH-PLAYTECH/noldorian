#!/usr/bin/env python3
"""noldorian-mcp — a zero-dependency stdio MCP server that installs and
orients the Everplay tooling (Noldorian CLIs + the snx spellbook) from the
private GitHub repos.

Register (Claude Code):
    claude mcp add noldorian -- python3 /path/to/noldorian/mcp/noldorian_mcp.py
or .mcp.json:
    {"mcpServers": {"noldorian": {"command": "python3",
        "args": ["/path/to/noldorian/mcp/noldorian_mcp.py"]}}}

Tools:
    orient            {topic: deploy|spells|bootstrap}  -> the xalakazam playbooks
    install_noldorian {packages?: [keyabra,...]}        -> pip user-installs from GitHub
    install_spells    {dest?: ~/spells}                 -> clone spellbook + snx shim
    doctor            {}                                -> what's installed / missing

Auth: uses `gh` if authenticated, else GITHUB_TOKEN. Pure stdlib; Python 3.8+.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = "Everplay-Tech/noldorian"
SPELLS_REPO = "Everplay-Tech/spells"
PACKAGES = ("keyabra", "xalakazam", "xadabra", "binabra", "xabra")
SNX_SHIM = """#!/bin/bash
# snx — global wrapper for the Snax CLI (installed by noldorian-mcp)
exec /usr/bin/env PYTHONPATH="$HOME/spells/snax:${PYTHONPATH}" python3 -m snax.cli "$@"
"""


def _sh(cmd, timeout=600, env=None):
    e = os.environ.copy()
    if env:
        e.update(env)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=e)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def _token() -> str | None:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    if shutil.which("gh"):
        code, out, _ = _sh(["gh", "auth", "token"], timeout=30)
        if code == 0 and out:
            return out
    return None


def _git_url(repo: str) -> str | None:
    tok = _token()
    if tok is None:
        return None
    return f"https://x-access-token:{tok}@github.com/{repo}.git"


def _user_bin() -> str:
    code, out, _ = _sh([sys.executable, "-m", "site", "--user-base"], timeout=30)
    return str(Path(out) / "bin") if code == 0 and out else "~/.local/bin"


def tool_orient(args: dict) -> dict:
    topic = (args or {}).get("topic", "deploy")
    try:
        import xalakazam  # installed?
        docs = {"deploy": xalakazam.DEPLOY, "spells": xalakazam.SPELLS,
                "bootstrap": xalakazam.BOOTSTRAP_HINT}
    except ImportError:
        # Fall back to the repo copy sitting next to this file.
        src = Path(__file__).resolve().parent.parent / "xalakazam" / "src"
        sys.path.insert(0, str(src))
        try:
            import xalakazam  # type: ignore
            docs = {"deploy": xalakazam.DEPLOY, "spells": xalakazam.SPELLS,
                    "bootstrap": xalakazam.BOOTSTRAP_HINT}
        except ImportError:
            return {"error": "xalakazam not installed and repo copy not found — "
                             "run install_noldorian first"}
    if topic == "all":
        return {"text": docs["deploy"] + "\n\n" + docs["spells"]}
    if topic not in docs:
        return {"error": f"unknown topic {topic!r} (deploy|spells|bootstrap|all)"}
    return {"text": docs[topic]}


def tool_install_noldorian(args: dict) -> dict:
    pkgs = (args or {}).get("packages") or list(PACKAGES)
    bad = [p for p in pkgs if p not in PACKAGES]
    if bad:
        return {"error": f"unknown packages {bad}; valid: {list(PACKAGES)}"}
    url = _git_url(REPO)
    if url is None:
        return {"error": "no GitHub auth: set GITHUB_TOKEN or authenticate gh"}
    results = {}
    for p in pkgs:
        code, out, err = _sh([sys.executable, "-m", "pip", "install", "--user",
                              "--quiet", f"git+{url}#subdirectory={p}"])
        results[p] = "ok" if code == 0 else f"FAILED: {(err or out)[-300:]}"
    return {"installed": results, "path_hint": f"ensure {_user_bin()} is on PATH"}


def tool_install_spells(args: dict) -> dict:
    dest = Path((args or {}).get("dest", "~/spells")).expanduser()
    if (dest / ".git").exists():
        note = "already present"
    else:
        url = _git_url(SPELLS_REPO)
        if url is None:
            return {"error": "no GitHub auth: set GITHUB_TOKEN or authenticate gh"}
        code, out, err = _sh(["git", "clone", "--depth", "1", url, str(dest)])
        if code != 0:
            return {"error": f"clone failed: {(err or out)[-300:]}"}
        note = "cloned"
    shim = Path.home() / "bin" / "snx"
    shim.parent.mkdir(parents=True, exist_ok=True)
    shim.write_text(SNX_SHIM)
    shim.chmod(0o755)
    code, out, err = _sh(["python3", "-m", "snax.cli", "list"],
                         env={"PYTHONPATH": str(dest / "snax")}, timeout=120)
    return {"spells_repo": str(dest), "state": note, "snx_shim": str(shim),
            "smoke": "ok" if code == 0 else f"snx list failed: {(err or out)[-200:]}",
            "path_hint": "ensure ~/bin is on PATH"}


def tool_doctor(_args: dict) -> dict:
    out = {"python": sys.version.split()[0], "user_bin": _user_bin()}
    for cli in ("keyabra", "xalakazam", "xadabra", "abra", "xabra", "snx", "gh"):
        out[cli] = shutil.which(cli) or "MISSING"
    out["spells_repo"] = "present" if (Path.home() / "spells" / ".git").exists() else "MISSING"
    out["github_auth"] = "ok" if _token() else "MISSING (gh login or GITHUB_TOKEN)"
    vault = Path.home() / ".config" / "keyabra" / "everplay-release.env"
    out["release_vault"] = str(vault) if vault.exists() else "not provisioned"
    return out


TOOLS = [
    {"name": "orient",
     "description": "The Everplay playbooks (xalakazam): how to deploy and strategically "
                    "use Noldorian and the snx spellbook. topic: deploy|spells|bootstrap|all",
     "inputSchema": {"type": "object", "properties": {
         "topic": {"type": "string", "enum": ["deploy", "spells", "bootstrap", "all"]}}}},
    {"name": "install_noldorian",
     "description": "pip user-install Noldorian CLIs from the private GitHub repo "
                    "(default: all of keyabra/xalakazam/xadabra/binabra/xabra).",
     "inputSchema": {"type": "object", "properties": {
         "packages": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "install_spells",
     "description": "Clone the Everplay snx spellbook (private repo) to dest (default "
                    "~/spells) and install the ~/bin/snx shim; smoke-tests `snx list`.",
     "inputSchema": {"type": "object", "properties": {"dest": {"type": "string"}}}},
    {"name": "doctor",
     "description": "Report what Everplay tooling is installed/missing on this machine.",
     "inputSchema": {"type": "object", "properties": {}}},
]

DISPATCH = {"orient": tool_orient, "install_noldorian": tool_install_noldorian,
            "install_spells": tool_install_spells, "doctor": tool_doctor}


def _reply(msg_id, result=None, error=None):
    resp = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        resp["error"] = error
    else:
        resp["result"] = result
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = msg.get("method")
        msg_id = msg.get("id")
        if method == "initialize":
            _reply(msg_id, {
                "protocolVersion": msg.get("params", {}).get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "noldorian", "version": "0.1.0"},
                "instructions": "Everplay tooling installer/orienter. Call `orient` first "
                                "(topic=deploy or spells) to load the playbooks; `doctor` to "
                                "see what's missing; install_* to fix it."})
        elif method == "notifications/initialized":
            continue  # notification, no reply
        elif method == "tools/list":
            _reply(msg_id, {"tools": TOOLS})
        elif method == "tools/call":
            params = msg.get("params", {})
            fn = DISPATCH.get(params.get("name"))
            if fn is None:
                _reply(msg_id, error={"code": -32602, "message": f"unknown tool {params.get('name')!r}"})
                continue
            try:
                result = fn(params.get("arguments") or {})
            except Exception as exc:  # noqa: BLE001 — surface, don't die
                result = {"error": f"{type(exc).__name__}: {exc}"}
            text = result.get("text") if isinstance(result, dict) else None
            payload = text if text is not None else json.dumps(result, indent=1)
            _reply(msg_id, {"content": [{"type": "text", "text": payload}],
                            "isError": bool(isinstance(result, dict) and result.get("error"))})
        elif msg_id is not None:
            _reply(msg_id, error={"code": -32601, "message": f"method {method!r} not supported"})


if __name__ == "__main__":
    main()
