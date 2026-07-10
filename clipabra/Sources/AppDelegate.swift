import AppKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    private let store = HistoryStore()
    private var watcher: PasteboardWatcher!
    private var panelController: HistoryPanelController!
    private let chordMonitor = ChordMonitor()
    private var statusItem: NSStatusItem!

    func applicationDidFinishLaunching(_ notification: Notification) {
        watcher = PasteboardWatcher(store: store)
        panelController = HistoryPanelController(store: store, watcher: watcher)
        watcher.start()

        chordMonitor.onToggleChord = { [weak self] in self?.panelController.toggle() }

        // Honest first-run permission flow: prompt once if missing; the app is
        // fully usable from the tray either way, and the menu shows live status.
        if ChordMonitor.accessibilityGranted() {
            chordMonitor.start()
        } else {
            _ = ChordMonitor.accessibilityGranted(prompt: true)
        }

        buildStatusItem()
    }

    private func buildStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        if let button = statusItem.button {
            button.image = NSImage(systemSymbolName: "doc.on.clipboard.fill",
                                   accessibilityDescription: "clipabra")
            button.action = #selector(statusClicked)
            button.target = self
            button.sendAction(on: [.leftMouseUp, .rightMouseUp])
        }
    }

    /// Left click: toggle the panel (the tray IS the chord fallback).
    /// Right click: menu with permission status + chord cheatsheet.
    @objc private func statusClicked() {
        if NSApp.currentEvent?.type == .rightMouseUp {
            statusItem.menu = buildMenu()
            statusItem.button?.performClick(nil)
            statusItem.menu = nil
        } else {
            panelController.toggle()
        }
    }

    private func buildMenu() -> NSMenu {
        let menu = NSMenu()
        menu.addItem(withTitle: "Show / hide history  (2+9, or click tray)",
                     action: #selector(togglePanel), keyEquivalent: "").target = self
        menu.addItem(withTitle: "Reveal selected: hold 4+7 while panel is open",
                     action: nil, keyEquivalent: "")
        menu.addItem(.separator())
        if ChordMonitor.accessibilityGranted() {
            let item = menu.addItem(withTitle: "Chords: active (Accessibility granted)",
                                    action: #selector(armChords), keyEquivalent: "")
            item.target = self
        } else {
            let item = menu.addItem(withTitle: "Chords inactive — grant Accessibility permission…",
                                    action: #selector(openAccessibilitySettings), keyEquivalent: "")
            item.target = self
        }
        menu.addItem(.separator())
        menu.addItem(withTitle: "Quit clipabra", action: #selector(quit), keyEquivalent: "q").target = self
        return menu
    }

    @objc private func togglePanel() { panelController.toggle() }

    /// Re-arm after the user grants permission (no relaunch needed).
    @objc private func armChords() { chordMonitor.start() }

    @objc private func openAccessibilitySettings() {
        _ = ChordMonitor.accessibilityGranted(prompt: true)
        let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")!
        NSWorkspace.shared.open(url)
    }

    @objc private func quit() { NSApp.terminate(nil) }
}
