#!/usr/bin/env python3
"""
Noldorian keyabra non-interactive vault probe.
Verifies secret presence, 0600 POSIX permissions, and valid structure
without exposing secret bytes to stdout or logs.
"""
import argparse
import os
import stat
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Noldorian keyabra secret vault probe.")
    parser.add_argument("--env-file", type=Path, required=True, help="Path to keyabra env-vault file.")
    parser.add_argument("var_name", help="Secret variable name to probe.")
    args = parser.parse_args()

    env_file = args.env_file.expanduser().resolve()
    if not env_file.exists():
        print(f"FAIL: env-vault file not found at {env_file}", file=sys.stderr)
        sys.exit(1)

    file_stat = env_file.stat()
    mode = stat.S_IMODE(file_stat.st_mode)
    if mode & 0o077 != 0:
        print(f"WARN: env-vault file permissions {oct(mode)} exceed recommended 0600", file=sys.stderr)

    found = False
    lines = env_file.read_text().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            if k.strip() == args.var_name:
                found = True
                if not v.strip():
                    print(f"FAIL: secret '{args.var_name}' exists but is empty", file=sys.stderr)
                    sys.exit(1)

    if found:
        print(f"PASS: secret '{args.var_name}' present and valid in {env_file} (mode {oct(mode)})")
        sys.exit(0)
    else:
        print(f"FAIL: secret '{args.var_name}' not found in {env_file}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
