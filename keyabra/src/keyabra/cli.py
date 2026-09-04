"""Undocumented 0.2.0 console-script shim. Prefer xabra."""

from xabra.operator import main

if __name__ == "__main__":
    raise SystemExit(main())
