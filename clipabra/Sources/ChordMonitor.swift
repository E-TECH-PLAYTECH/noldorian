import AppKit
import Foundation

/// Global two-key chord detection (LOCKED: show/hide = 2+9 co-held 150 ms).
///
/// Simultaneous *character* keys cannot be done with RegisterEventHotKey, so
/// this is a CGEventTap — which requires Accessibility permission. The honest
/// flow: `accessibilityGranted(prompt:)` drives the first-run prompt, the tray
/// menu shows live status, and the app stays fully usable from the tray while
/// permission is missing (chords simply inactive).
///
/// DELAY-AND-REPLAY (no first-keystroke leak): a chord-member keyDown is
/// swallowed and held. If the second member arrives and both stay co-held for
/// 150 ms, the chord fires and the held events are discarded — nothing ever
/// types. If the window expires, a non-member key arrives, or a member is
/// released early (typing rollover), the held events are re-posted in order,
/// tagged with `replayTag` in eventSourceUserData so they skip this tap on
/// re-entry. Cost, stated honestly: an isolated "2" or "9" keystroke lands
/// ~150 ms late; mixed typing flushes immediately on the next non-member key.
/// Key-repeats of a held member are dropped inside the window (the window is
/// shorter than the system's initial repeat delay, so in practice none occur);
/// chords with Command/Control/Option held are ignored and pass through.
final class ChordMonitor {
    /// ANSI keycodes: 2 = 19, 9 = 25.
    static let toggleChord: Set<Int64> = [19, 25]
    static let coHoldSeconds: TimeInterval = 0.15
    /// Marks replayed events so they pass straight through our own tap.
    static let replayTag: Int64 = 0xC11ABA

    var onToggleChord: (() -> Void)?

    private enum State {
        case idle
        case holdingFirst(code: Int64)
        case holdingBoth
        case fired
    }

    private var state: State = .idle
    private var pending: [CGEvent] = []
    private var firedMembersDown = Set<Int64>()
    private var replayTimer: Timer?
    private var fireTimer: Timer?
    private var tap: CFMachPort?
    private var runLoopSource: CFRunLoopSource?

    static func accessibilityGranted(prompt: Bool = false) -> Bool {
        let key = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String
        return AXIsProcessTrustedWithOptions([key: prompt] as CFDictionary)
    }

    /// Returns true if the tap is live. Safe to call again after permission
    /// is granted (tray menu offers a re-arm).
    @discardableResult
    func start() -> Bool {
        guard tap == nil else { return true }
        guard Self.accessibilityGranted() else { return false }
        let mask = (1 << CGEventType.keyDown.rawValue) | (1 << CGEventType.keyUp.rawValue)
        guard let created = CGEvent.tapCreate(
            tap: .cgSessionEventTap,
            place: .headInsertEventTap,
            options: .defaultTap,
            eventsOfInterest: CGEventMask(mask),
            callback: { _, type, event, refcon in
                let monitor = Unmanaged<ChordMonitor>.fromOpaque(refcon!).takeUnretainedValue()
                return monitor.handle(type: type, event: event)
            },
            userInfo: Unmanaged.passUnretained(self).toOpaque()
        ) else { return false }
        tap = created
        runLoopSource = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, created, 0)
        CFRunLoopAddSource(CFRunLoopGetMain(), runLoopSource, .commonModes)
        CGEvent.tapEnable(tap: created, enable: true)
        return true
    }

    // MARK: tap callback (tap source is on the main run loop — timers are safe)

    private func handle(type: CGEventType, event: CGEvent) -> Unmanaged<CGEvent>? {
        if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput {
            if let tap { CGEvent.tapEnable(tap: tap, enable: true) }
            return Unmanaged.passUnretained(event)
        }
        // Replayed events pass straight through — never reprocessed.
        if event.getIntegerValueField(.eventSourceUserData) == Self.replayTag {
            return Unmanaged.passUnretained(event)
        }

        let code = event.getIntegerValueField(.keyboardEventKeycode)
        let isMember = Self.toggleChord.contains(code)
        let modified = !event.flags.intersection([.maskCommand, .maskControl, .maskAlternate]).isEmpty
        let isRepeat = event.getIntegerValueField(.keyboardEventAutorepeat) == 1
        let pass = Unmanaged.passUnretained(event)

        switch (type, state) {
        case (.keyDown, .idle):
            guard isMember, !modified, !isRepeat, let copy = event.copy() else { return pass }
            pending = [copy]
            state = .holdingFirst(code: code)
            replayTimer = Timer.scheduledTimer(withTimeInterval: Self.coHoldSeconds, repeats: false) { [weak self] _ in
                self?.flushPending() // lone member: window expired → it types, ~150 ms late
            }
            return nil

        case (.keyDown, .holdingFirst(let first)):
            if isMember, code != first, !modified, !isRepeat, let copy = event.copy() {
                pending.append(copy)
                replayTimer?.invalidate(); replayTimer = nil
                state = .holdingBoth
                fireTimer = Timer.scheduledTimer(withTimeInterval: Self.coHoldSeconds, repeats: false) { [weak self] _ in
                    self?.fireIfStillHeld()
                }
                return nil
            }
            if isMember, code == first, isRepeat { return nil } // drop in-window repeats
            flushPending() // typing: replay the held member, current key follows
            return pass

        case (.keyDown, .holdingBoth):
            if isMember, isRepeat { return nil }
            fireTimer?.invalidate(); fireTimer = nil
            flushPending() // interrupted mid-chord: replay both, current key follows
            return pass

        case (.keyDown, .fired):
            return isMember ? nil : pass // swallow chord-key repeats until release

        case (.keyUp, .holdingFirst(let first)) where code == first:
            flushPending() // plain tap of a member: replay its down…
            postTagged(event) // …then its up, in order
            return nil

        case (.keyUp, .holdingBoth) where isMember:
            fireTimer?.invalidate(); fireTimer = nil
            flushPending() // rollover ("29" typed fast): replay downs…
            postTagged(event) // …then this up — nothing lost, chord (correctly) never fires
            return nil

        case (.keyUp, .fired) where isMember:
            firedMembersDown.remove(code)
            if firedMembersDown.isEmpty { state = .idle }
            return nil

        default:
            return pass
        }
    }

    private func fireIfStillHeld() {
        fireTimer = nil
        guard case .holdingBoth = state else { return }
        pending.removeAll() // chord confirmed — the held downs are never replayed
        firedMembersDown = Self.toggleChord
        state = .fired
        DispatchQueue.main.async { self.onToggleChord?() }
    }

    /// Re-post every held event in order, tagged so our tap skips them.
    private func flushPending() {
        replayTimer?.invalidate(); replayTimer = nil
        for held in pending { postTagged(held) }
        pending.removeAll()
        state = .idle
    }

    private func postTagged(_ event: CGEvent) {
        let out = event.copy() ?? event
        out.setIntegerValueField(.eventSourceUserData, value: Self.replayTag)
        out.post(tap: .cgSessionEventTap)
    }
}
