"""Owner-side prompt used only as a child of the root broker."""

from __future__ import annotations

import base64
import getpass
import json
import platform
import subprocess
import sys
from typing import Any, Mapping


def _prompt_text(request: Mapping[str, Any]) -> str:
    resources = json.dumps(request.get("resources", {}), sort_keys=True)
    operations = ", ".join(str(item) for item in request.get("operations", []))
    return (
        "Noldorian is requesting a credential.\n\n"
        f"Capability: {request.get('capability_id', '')}\n"
        f"Provider: {request.get('provider', '')}\n"
        f"Purpose: {request.get('purpose', '')}\n"
        f"Operations: {operations}\n"
        f"Scope: {resources}\n\n"
        "Enter the credential in the hidden field. It will be sent only to "
        "the local Noldorian broker and will not be shown to the agent."
    )


def _macos_prompt(request: Mapping[str, Any]) -> str | None:
    # The credential is returned through this owner's private child process,
    # never through argv or an agent-facing socket.  The JXA source contains no
    # credential; it only supplies the human-readable request to the dialog.
    title = json.dumps("Noldorian — Human Gate", ensure_ascii=False)
    body = json.dumps(_prompt_text(request), ensure_ascii=False)
    script = f"""
ObjC.import('Cocoa');
const app = Application.currentApplication();
app.includeStandardAdditions = true;
try {{
  const answer = app.displayDialog({body}, {{
    defaultAnswer: '',
    hiddenAnswer: true,
    buttons: ['Cancel', 'Approve & Save'],
    defaultButton: 'Approve & Save',
    cancelButton: 'Cancel',
    withTitle: {title}
  }});
  console.log(JSON.stringify({{status: 'approved', secret: answer.textReturned}}));
}} catch (error) {{
  console.log(JSON.stringify({{status: 'cancelled'}}));
}}
"""
    try:
        completed = subprocess.run(
            ["/usr/bin/osascript", "-l", "JavaScript", "-e", script],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    lines = [line.strip() for line in (completed.stdout or "").splitlines() if line.strip()]
    if not lines:
        return None
    try:
        response = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None
    return response.get("secret") if response.get("status") == "approved" else None


def main() -> int:
    try:
        request = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        print(json.dumps({"status": "failed", "error": "invalid_request"}))
        return 1
    if not isinstance(request, dict):
        print(json.dumps({"status": "failed", "error": "invalid_request"}))
        return 1

    secret: str | None
    if platform.system() == "Darwin":
        secret = _macos_prompt(request)
    elif sys.stdin.isatty():
        secret = getpass.getpass("Noldorian credential (hidden): ")
        if secret != getpass.getpass("Noldorian credential (again): "):
            secret = None
    else:
        secret = None

    if not secret:
        print(json.dumps({"status": "cancelled"}))
        return 0
    encoded = base64.b64encode(secret.encode("utf-8")).decode("ascii")
    secret = ""
    print(json.dumps({"status": "approved", "secret_b64": encoded}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
