# xalakazam — the Everplay orienter

Callable memory: `xalakazam --deploy` (Noldorian playbook) and
`xalakazam --spells` (snx spellbook playbook) print everything an agent or
human needs to install and strategically use the Everplay tooling on any
machine — docs are embedded in the package, no checkout needed.

```
pip install "git+https://github.com/Everplay-Tech/noldorian.git#subdirectory=xalakazam"
xalakazam --deploy
xalakazam --spells
xalakazam --cursor-sdk-enable
```

`--cursor-sdk-enable` opens Cursor's User API Key page, then hands the copied
key directly to Keyabra's hidden prompt. Keyabra validates the key, stores it
in Google Secret Manager over stdin, reads it back, and validates it again.
Neither tool prints or persists the credential outside the designated secret.

This rite is for bounded internal evaluation. It stores a credential only; it
does not install or redistribute the Cursor SDK and does not grant production,
customer-delivery, or redistribution rights. Those uses require separate
commercial-rights clearance and dependency review.

Proprietary — © 2026 Everplay-Tech LLC.
