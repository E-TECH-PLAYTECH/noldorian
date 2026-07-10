# clipabra — the -abra family clipboard manager

A macOS menu-bar clipboard history manager that takes `org.nspasteboard.ConcealedType`
seriously: concealed captures are masked, memory-only, TTL-wiped, and revealable only
through a deliberate two-key chord. Every capture / reveal / copy-back / wipe leaves a
TULKAS-style audit row. Sibling of `keyabra` (whose `copy` command writes the concealed
entries this app honors).

## Locked design (2026-07-09 — /noscope, /sherlock; no 'or's)

| Decision | Locked value |
|---|---|
| Name | **clipabra** — the -abra family |
| Tech | **Swift/AppKit menu-bar app** (NSStatusItem + NSPanel/SwiftUI). Simultaneous character-key chords are impossible with RegisterEventHotKey, so the global chord is a **CGEventTap** (needs Accessibility); the reveal chord is a **local NSEvent monitor** (panel-scope, no permission, consumes keys). |
| Repo | **Standalone private repo `Everplay-Tech/clipabra`** — noldorian stays pip-CLI-only |
| History depth | **50 entries**, consecutive-duplicate dedupe |
| Persistence | **Normal entries** persist to `~/Library/Application Support/clipabra/history.json` (0600), survive relaunch. **Concealed entries: memory-only, never on disk, 5-minute TTL** then wiped (audit row `wipe`). `org.nspasteboard.TransientType` entries are never recorded at all. |
| Reveal chord | **Hold 4+7** (ANSI 21+26) while the panel is frontmost — hold-to-reveal, releases re-mask instantly (dead-man switch); keys consumed, never typed |
| Show/hide chord | **2+9** (ANSI 19+25) co-held 150 ms, global, toggles the panel |
| Tray | Left-click = toggle panel (the chord fallback/initiation). Right-click menu = chord cheatsheet + live Accessibility status + grant/re-arm + Quit. First run prompts honestly; app fully usable trayside without the permission. |
| Receipts | `audit.jsonl` (0600): ts / event (`capture`,`reveal`,`copyback`,`wipe`) / id / len / concealed / sha256-8 fingerprint — **never the value** |
| Sync | **Local-only by construction** — the app never syncs anything anywhere. (Universal Clipboard is a system behavior; the concealed TTL is the mitigation.) |

Global-chord input semantics (delay-and-replay — no keystroke leak): a chord-member
keyDown is swallowed and held; the chord fires only after both members are co-held
150 ms (held events discarded — nothing ever types). Otherwise the held events are
re-posted in order, tagged via `eventSourceUserData` so they skip our own tap on
re-entry. The honest cost: an **isolated "2" or "9" keystroke lands ~150 ms late**;
in mixed typing the next non-member key flushes the queue immediately, and fast-rolled
"29" replays both keys intact and (correctly) never fires. Key-repeats inside the
window are dropped (the window is shorter than the system's initial repeat delay, so
in practice none occur); Cmd/Ctrl/Opt-modified members pass through untouched. The
reveal chord (4+7) needed no such treatment — checked before touching: the local
monitor consumes all member events while the panel is key, and the panel has no text
inputs, so there is nothing to leak into.

## Build

```bash
xcodegen generate
xcodebuild -project clipabra.xcodeproj -scheme clipabra -configuration Debug build
```

macOS 14+. `LSUIElement` — no Dock icon.
