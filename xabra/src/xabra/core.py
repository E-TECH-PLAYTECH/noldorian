"""Resolve, fetch, verify, install — the machinery behind the xabra CLI."""

from __future__ import annotations

import fnmatch
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path

from xabra import BACKUP_DIR, RECEIPT_DIR

APPLICATIONS = Path("/Applications")
BIN_DIR = Path.home() / ".local/bin"


def sh(args: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, **kw)


def require_gh() -> str:
    path = shutil.which("gh")
    if not path:
        raise SystemExit("xabra: 'gh' not found — install GitHub CLI and run `gh auth login`")
    return path


# ---------------------------------------------------------------- installed side

def installed_app_info(spec: dict) -> dict:
    """Version/build of the app as it exists on this machine, or installed=False."""
    if spec["kind"] == "cli":
        path = shutil.which(spec["bin"]) or (
            str(BIN_DIR / spec["bin"]) if (BIN_DIR / spec["bin"]).is_file() else None
        )
        if not path:
            return {"installed": False}
        ver = sh([path, "--version"])
        return {"installed": True, "path": path, "version": (ver.stdout or ver.stderr).strip()[:80]}
    app = APPLICATIONS / spec["app"]
    plist = app / "Contents/Info.plist"
    if not plist.is_file():
        return {"installed": False}

    # `defaults read` rather than plistlib: pyexpat is broken in some
    # Homebrew Pythons, and Info.plist may be binary anyway.
    def _key(name: str) -> str | None:
        out = sh(["defaults", "read", str(plist.with_suffix("")), name])
        return (out.stdout.strip() or None) if out.returncode == 0 else None

    return {
        "installed": True,
        "path": str(app),
        "version": _key("CFBundleShortVersionString"),
        "build": _key("CFBundleVersion"),
    }


# ---------------------------------------------------------------- available side

def _gh_json(path: str) -> dict | list | None:
    out = sh([require_gh(), "api", path])
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def resolve_source(spec: dict) -> dict:
    """First source that currently resolves: what would be installed, from where."""
    for src in spec.get("sources", []):
        if src["type"] == "release":
            rel = _gh_json(f"repos/{src['repo']}/releases/latest")
            if not isinstance(rel, dict) or "assets" not in rel:
                continue
            assets = [a["name"] for a in rel["assets"] if fnmatch.fnmatch(a["name"], src["asset"])]
            if assets:
                return {**src, "resolved": rel["tag_name"], "asset_name": assets[0]}
        elif src["type"] == "artifact":
            arts = _gh_json(f"repos/{src['repo']}/actions/artifacts?per_page=50")
            if not isinstance(arts, dict):
                continue
            match = [
                a for a in arts.get("artifacts", [])
                if fnmatch.fnmatch(a["name"], src["pattern"]) and not a["expired"]
            ]
            if match:
                newest = max(match, key=lambda a: a["created_at"])
                return {**src, "resolved": newest["name"], "artifact_id": newest["id"]}
        elif src["type"] == "local":
            hits = sorted(Path(src["path"]).expanduser().parent.glob(Path(src["path"]).name),
                          key=lambda p: p.stat().st_mtime, reverse=True)
            if hits:
                return {**src, "resolved": str(hits[0])}
    return {}


def fetch(source: dict, workdir: Path) -> Path:
    """Materialize the payload (dmg or tar.gz) from a resolved source into workdir."""
    gh = require_gh()
    if source["type"] == "release":
        out = sh([gh, "release", "download", source["resolved"], "-R", source["repo"],
                  "-p", source["asset_name"], "-D", str(workdir)])
        if out.returncode != 0:
            raise SystemExit(f"xabra: release download failed: {out.stderr.strip()}")
        return workdir / source["asset_name"]
    if source["type"] == "artifact":
        zip_path = workdir / "artifact.zip"
        with open(zip_path, "wb") as fh:
            out = subprocess.run(
                [gh, "api", f"repos/{source['repo']}/actions/artifacts/{source['artifact_id']}/zip"],
                stdout=fh, stderr=subprocess.PIPE, text=False)
        if out.returncode != 0:
            raise SystemExit(f"xabra: artifact download failed: {out.stderr.decode()[:200]}")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(workdir)
        payloads = list(workdir.rglob("*.dmg")) + list(workdir.rglob("*.tar.gz"))
        if not payloads:
            raise SystemExit(f"xabra: artifact {source['resolved']} contains no dmg/tar.gz")
        return payloads[0]
    if source["type"] == "local":
        return Path(source["resolved"])
    raise SystemExit(f"xabra: unknown source type {source['type']}")


# ---------------------------------------------------------------- install: .app

def _mounted_app(mount: Path) -> Path:
    apps = list(mount.glob("*.app"))
    if not apps:
        raise SystemExit(f"xabra: no .app inside dmg mount {mount}")
    return apps[0]


def install_dmg_app(spec: dict, dmg: Path, receipt: dict) -> None:
    mount = Path(tempfile.mkdtemp(prefix="xabra-mnt-"))
    out = sh(["hdiutil", "attach", str(dmg), "-nobrowse", "-readonly",
              "-mountpoint", str(mount)])
    if out.returncode != 0:
        raise SystemExit(f"xabra: hdiutil attach failed: {out.stderr.strip()}")
    try:
        src_app = _mounted_app(mount)
        gate = sh(["spctl", "--assess", "--type", "execute", "-v", str(src_app)])
        receipt["gatekeeper"] = (gate.stderr or gate.stdout).strip()
        if gate.returncode != 0:
            raise SystemExit(f"xabra: Gatekeeper rejected {src_app.name}: {receipt['gatekeeper']}")
        csign = sh(["codesign", "--verify", "--deep", "--strict", str(src_app)])
        if csign.returncode != 0:
            raise SystemExit(f"xabra: codesign verify failed: {csign.stderr.strip()}")

        target = APPLICATIONS / spec["app"]
        sh(["osascript", "-e", f'tell application "{spec["app"].removesuffix(".app")}" to quit'])
        time.sleep(1)
        if target.exists():
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            backup = BACKUP_DIR / f"{spec['app']}.{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
            sh(["ditto", str(target), str(backup)])
            receipt["backup"] = str(backup)
            shutil.rmtree(target)
        copy = sh(["ditto", str(src_app), str(target)])
        if copy.returncode != 0:
            raise SystemExit(f"xabra: ditto install failed: {copy.stderr.strip()}")
        receipt["installed_path"] = str(target)
    finally:
        sh(["hdiutil", "detach", str(mount), "-quiet"])


# ---------------------------------------------------------------- install: cli

def install_cli(spec: dict, tarball: Path, receipt: dict) -> None:
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="xabra-cli-") as td:
        with tarfile.open(tarball) as tf:
            try:
                tf.extractall(td, filter="data")
            except TypeError:  # Python < 3.12 has no filter kwarg
                tf.extractall(td)
        hits = [p for p in Path(td).rglob(spec["bin"]) if p.is_file()]
        if not hits:
            raise SystemExit(f"xabra: '{spec['bin']}' not found inside {tarball.name}")
        target = BIN_DIR / spec["bin"]
        shutil.copy2(hits[0], target)
        target.chmod(0o755)
        receipt["installed_path"] = str(target)


# ---------------------------------------------------------------- receipts

def bank_receipt(receipt: dict) -> Path:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    slug = re.sub(r"[^a-z0-9-]", "-", receipt.get("app", "unknown").lower())
    path = RECEIPT_DIR / f"{stamp}__{receipt.get('action', 'act')}__{slug}.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    return path


def emit(receipt: dict, as_json: bool) -> None:
    if as_json:
        json.dump(receipt, sys.stdout, indent=2)
        print()
    else:
        ok = "ok" if receipt.get("ok") else "FAILED"
        print(f"xabra {receipt.get('action')}: {receipt.get('app')} — {ok}")
        for key in ("version", "build", "resolved", "installed_path", "backup", "receipt"):
            if receipt.get(key):
                print(f"  {key}: {receipt[key]}")
