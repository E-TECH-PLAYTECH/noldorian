# xalakazam

Noldorian orienter: callable memory for installing and using the public
package on any machine. Docs are embedded in the wheel.

```
python3 -m pip install noldorian
xalakazam --deploy
xalakazam --owner-actions
```

`xalakazam --owner-actions` prints the owner checkpoint rite: ask once for an
owner-only UI, purchase, device, secret, client-login, or host permission
action; pause; then perform one fresh verification after the owner's
non-secret confirmation. Credentials go through `xabra env set` / `xabra run`,
never through chat.

Licensed under the [Apache License 2.0](LICENSE).
