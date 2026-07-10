import AppKit
import SwiftUI

/// UI state shared between the panel's local key monitor and the SwiftUI view.
final class PanelState: ObservableObject {
    @Published var revealHeld = false
    @Published var selectedID: UUID?
}

/// The recallable history panel. Reveal chord (LOCKED: 4+7, hold-to-reveal) is
/// a LOCAL NSEvent monitor — it only exists while the panel is key, needs no
/// Accessibility permission, and consumes the chord keys so nothing types
/// anywhere. Releasing either key re-masks instantly (dead-man switch).
final class HistoryPanelController {
    /// ANSI keycodes: 4 = 21, 7 = 26.
    static let revealChord: Set<UInt16> = [21, 26]

    let state = PanelState()
    private let store: HistoryStore
    private var panel: NSPanel?
    private var localMonitor: Any?
    private var revealDown = Set<UInt16>()

    init(store: HistoryStore, watcher: PasteboardWatcher) {
        self.store = store
        buildPanel(watcher: watcher)
    }

    var isVisible: Bool { panel?.isVisible ?? false }

    func toggle() {
        guard let panel else { return }
        if panel.isVisible {
            hide()
        } else {
            panel.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            installMonitor()
        }
    }

    func hide() {
        state.revealHeld = false
        revealDown.removeAll()
        removeMonitor()
        panel?.orderOut(nil)
    }

    private func buildPanel(watcher: PasteboardWatcher) {
        let p = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 440, height: 480),
            styleMask: [.titled, .closable, .utilityWindow],
            backing: .buffered,
            defer: false
        )
        p.title = "clipabra"
        p.isFloatingPanel = true
        p.hidesOnDeactivate = false
        p.isReleasedWhenClosed = false
        p.center()
        p.contentView = NSHostingView(
            rootView: HistoryView(store: store, state: state) { [weak self] entry in
                guard let self else { return }
                self.store.copyBack(entry, watcher: watcher)
            }
        )
        panel = p
    }

    // MARK: local reveal-chord monitor

    private func installMonitor() {
        guard localMonitor == nil else { return }
        localMonitor = NSEvent.addLocalMonitorForEvents(matching: [.keyDown, .keyUp]) { [weak self] event in
            guard let self else { return event }
            guard Self.revealChord.contains(event.keyCode) else { return event }
            if event.type == .keyDown {
                self.revealDown.insert(event.keyCode)
            } else {
                self.revealDown.remove(event.keyCode)
            }
            let held = Self.revealChord.isSubset(of: self.revealDown)
            if held != self.state.revealHeld {
                self.state.revealHeld = held
                if held, let id = self.state.selectedID,
                   let entry = self.store.entries.first(where: { $0.id == id }) {
                    AuditLog.append(event: "reveal", entry: entry)
                }
            }
            return nil // chord keys never reach the app's text fields
        }
    }

    private func removeMonitor() {
        if let localMonitor { NSEvent.removeMonitor(localMonitor) }
        localMonitor = nil
    }
}
