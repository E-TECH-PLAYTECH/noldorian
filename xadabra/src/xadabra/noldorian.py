from __future__ import annotations

import argparse
import getpass
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

DEFAULT_ORG = "Everplay-Tech"
DEFAULT_REPO = "noldorian"
DEFAULT_TAG = "v0.2.0"
PACKAGES = ("binabra", "keyabra", "xadabra")
PYPI_VERSIONS = ("0.1.0", "0.1.1")


def _prompt(label: str, default: str) -> str:
    raw = input(f"{label} [{default}]: ").strip()
    return raw or default


def _run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> int:
    print(f"+ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check).returncode


def _twine_path() -> str | None:
    for candidate in (
        shutil.which("twine"),
        str(Path.home() / "Library/Python/3.9/bin/twine"),
        str(Path.home() / ".local/bin/twine"),
    ):
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def cmd_guide(_: argparse.Namespace) -> int:
    print(
        textwrap.dedent(
            f"""
            xadabra noldorian — legacy release workflow
            =============================================

            The normal install is the unified public distribution:
              python3 -m pip install noldorian==0.2.0
              # installs noldorian, keyabra, xadabra, xabra, abra, xalakazam

            Legacy source workflow (operator-only):
              xadabra noldorian pack          # scaffold ~/noldorian
              xadabra noldorian push          # commit, tag, push
              xadabra noldorian install       # print a pinned install command
              xadabra noldorian yank          # legacy PyPI maintenance
              xadabra noldorian script        # paste-runner template for custom flow

            Or one paste block:
              xadabra noldorian script | pbcopy
              # edit if needed, then: xadabra
            """
        ).strip()
    )
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    dest = Path(args.dest).expanduser().resolve()
    projects = Path(args.projects_dir).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    for name in PACKAGES:
        src = projects / name
        if not src.is_dir():
            print(f"xadabra: missing {src}", file=sys.stderr)
            return 1
        dst = dest / name
        if dst.exists() and not args.force:
            print(f"xadabra: {dst} exists — use --force to refresh", file=sys.stderr)
            return 1
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(
            src,
            dst,
            ignore=shutil.ignore_patterns("dist", "build", "*.egg-info", "__pycache__", ".pytest_cache"),
        )
        print(f"packed {name} → {dst}")

    spells_doc = Path.home() / "spells" / "NOLDORIAN.md"
    if spells_doc.is_file():
        shutil.copy2(spells_doc, dest / "NOLDORIAN.md")

    gitignore = dest / ".gitignore"
    if not gitignore.exists() or args.force:
        gitignore.write_text(
            "__pycache__/\n*.py[cod]\ndist/\nbuild/\n*.egg-info/\n.eggs/\n.pytest_cache/\n.DS_Store\n",
            encoding="utf-8",
        )

    readme = dest / "README.md"
    if not readme.exists() or args.force:
        lines = [
            "# Noldorian",
            "",
            "Unified Noldorian distribution — Everplay-Tech LLC.",
            "",
            "| Package | CLI |",
            "|---------|-----|",
        ]
        cli_names = {"binabra": "abra", "keyabra": "keyabra", "xadabra": "xadabra"}
        org = args.org or DEFAULT_ORG
        repo = args.repo or DEFAULT_REPO
        tag = args.tag or DEFAULT_TAG
        for pkg in PACKAGES:
            cli = cli_names[pkg]
            lines.append(f"| {pkg} | `{cli}` |")
        lines += ["", "## Install (public unified package)", ""]
        lines.append("python3 -m pip install noldorian==0.2.0")
        lines.append("# Source pin for maintainers:")
        lines.append(f'python3 -m pip install "git+ssh://git@github.com/{org}/{repo}.git@{tag}"')
        lines += [
            "",
            "The package also installs the family compatibility CLIs.",
            "",
        ]
        readme.write_text("\n".join(lines), encoding="utf-8")

    print(f"\npacked monorepo at {dest}")
    print("next: xadabra noldorian push")
    return 0


def _git_config(repo: Path, key: str) -> str:
    result = subprocess.run(
        ["git", "config", key],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _ensure_git_identity(repo: Path) -> int:
    """Prompt and set repo-local git user.name / user.email if missing."""
    name = _git_config(repo, "user.name")
    email = _git_config(repo, "user.email")
    if not name:
        name = _prompt("Git user.name", "ShelleyGuitar")
        if _run(["git", "config", "user.name", name], cwd=repo) != 0:
            return 1
    elif name:
        name = _git_config(repo, "user.name")

    email = _git_config(repo, "user.email")
    if not email or "YOUR_" in email.upper() or email.endswith("@example.com"):
        print("Git user.email: GitHub primary or @users.noreply.github.com")
        print("  → https://github.com/settings/emails")
        email = _prompt("Git user.email", "")
        if not email or "YOUR_" in email.upper():
            print("xadabra: real email required for git commit", file=sys.stderr)
            return 1
        if _run(["git", "config", "user.email", email], cwd=repo) != 0:
            return 1
    print(f"xadabra: git identity → {name} <{email}> (repo-local)")
    return 0


def cmd_push(args: argparse.Namespace) -> int:
    dest = Path(args.dest).expanduser().resolve()
    if not dest.is_dir():
        print(f"xadabra: {dest} missing — run: xadabra noldorian pack", file=sys.stderr)
        return 1

    if not (dest / ".git").is_dir():
        if _run(["git", "init"], cwd=dest) != 0:
            return 1
        _run(["git", "branch", "-M", "main"], cwd=dest, check=False)

    if _ensure_git_identity(dest) != 0:
        return 1

    org = args.org or _prompt("GitHub org", DEFAULT_ORG)
    repo = args.repo or _prompt("GitHub repo", DEFAULT_REPO)
    tag = args.tag or _prompt("Git tag", DEFAULT_TAG)
    remote = f"git@github.com:{org}/{repo}.git"

    if args.message:
        message = args.message
    else:
        message = _prompt("Commit message", f"Noldorian: {', '.join(PACKAGES)} ({tag})")

    _run(["git", "add", "-A"], cwd=dest)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=dest, capture_output=True, text=True)
    if status.stdout.strip():
        if _run(["git", "commit", "-m", message], cwd=dest) != 0:
            return 1
    else:
        print("xadabra: nothing to commit")

    _run(["git", "tag", "-a", tag, "-m", tag], cwd=dest, check=False)

    remotes = subprocess.run(["git", "remote"], cwd=dest, capture_output=True, text=True)
    if "origin" not in remotes.stdout.split():
        _run(["git", "remote", "add", "origin", remote], cwd=dest)
    else:
        _run(["git", "remote", "set-url", "origin", remote], cwd=dest)

    if args.dry_run:
        print(f"xadabra: dry-run — would push to {remote}")
        return 0

    if _run(["git", "push", "-u", "origin", "main"], cwd=dest) != 0:
        return 1
    if _run(["git", "push", "origin", tag], cwd=dest) != 0:
        return 1

    print(f"\n✅ pushed {org}/{repo} @ {tag}")
    print(f"   https://github.com/{org}/{repo}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    if args.package == "all":
        line = "python3 -m pip install --user --force-reinstall noldorian==0.2.0"
        print(line)
        if args.run:
            return _run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--user",
                    "--force-reinstall",
                    "noldorian==0.2.0",
                ]
            )
        return 0

    org = args.org or _prompt("GitHub org", DEFAULT_ORG)
    repo = args.repo or _prompt("GitHub repo", DEFAULT_REPO)
    tag = args.tag or _prompt("Git tag", DEFAULT_TAG)
    pkgs = PACKAGES if args.package == "all" else (args.package,)

    lines = []
    for pkg in pkgs:
        spec = f'git+ssh://git@github.com/{org}/{repo}.git@{tag}#subdirectory={pkg}'
        line = f"python3 -m pip install --user --force-reinstall \"{spec}\""
        lines.append(line)
        print(line)

    if args.run:
        for line in lines:
            cmd = line.split(" ", 3)[-1].strip('"')
            if _run([sys.executable, "-m", "pip", "install", "--user", "--force-reinstall", cmd]) != 0:
                return 1
    return 0


def cmd_yank(args: argparse.Namespace) -> int:
    twine = _twine_path()
    if not twine:
        print("xadabra: twine not found — pip install twine", file=sys.stderr)
        return 1

    token = getpass.getpass("PyPI token (pypi-...): ")
    env = os.environ.copy()
    env["TWINE_USERNAME"] = "__token__"
    env["TWINE_PASSWORD"] = token

    packages = list(args.packages) if args.packages else list(PACKAGES)
    versions = list(args.versions) if args.versions else list(PYPI_VERSIONS)

    if not args.yes:
        print("Will yank from PyPI:")
        for pkg in packages:
            for ver in versions:
                print(f"  {pkg} {ver}")
        if input("Yank? [y/N] ").strip().lower() not in ("y", "yes"):
            print("cancelled")
            return 0

    for pkg in packages:
        for ver in versions:
            print(f"yanking {pkg} {ver} ...")
            rc = subprocess.run([twine, "yank", pkg, ver, "-y"], env=env).returncode
            if rc != 0:
                print(f"xadabra: yank failed for {pkg} {ver}", file=sys.stderr)
                return rc

    print("✅ yank complete (versions still exist on PyPI but are marked yanked)")
    return 0


def cmd_script(args: argparse.Namespace) -> int:
    path = Path(__file__).resolve().parent / "templates" / "noldorian-private-github.sh"
    if args.print_path:
        print(path)
        return 0
    text = path.read_text(encoding="utf-8")
    print(text)
    if args.copy:
        subprocess.run(["pbcopy"], input=text, text=True, check=False)
        print("# copied to clipboard — run: xadabra", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="xadabra noldorian",
        description="Legacy operator workflow for the unified Noldorian package",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("guide", help="print walkthrough checklist")
    p.set_defaults(func=cmd_guide)

    p = sub.add_parser("pack", help="scaffold monorepo (default ~/noldorian)")
    p.add_argument("--dest", default="~/noldorian")
    p.add_argument("--projects-dir", default="~/noldorian")
    p.add_argument("--org", default=None)
    p.add_argument("--repo", default=None)
    p.add_argument("--tag", default=None)
    p.add_argument("--force", action="store_true", help="overwrite existing package copies")
    p.set_defaults(func=cmd_pack)

    p = sub.add_parser("push", help="git commit, tag, and push to GitHub")
    p.add_argument("--dest", default="~/noldorian")
    p.add_argument("--org", default=None)
    p.add_argument("--repo", default=None)
    p.add_argument("--tag", default=None)
    p.add_argument("-m", "--message", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_push)

    p = sub.add_parser("install", help="print the unified noldorian install command")
    p.add_argument("--org", default=None)
    p.add_argument("--repo", default=None)
    p.add_argument("--tag", default=None)
    p.add_argument("--package", default="all", choices=[*PACKAGES, "all"])
    p.add_argument("--run", action="store_true", help="run pip install")
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("yank", help="yank public PyPI versions (token prompt)")
    p.add_argument("packages", nargs="*", metavar="PKG")
    p.add_argument("--versions", nargs="+", default=None)
    p.add_argument("-y", "--yes", action="store_true")
    p.set_defaults(func=cmd_yank)

    p = sub.add_parser("script", help="emit xadabra paste template for full flow")
    p.add_argument("--copy", action="store_true", help="copy template to clipboard (pbcopy)")
    p.add_argument("--path", action="store_true", dest="print_path")
    p.set_defaults(func=cmd_script)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
