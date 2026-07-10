import AppKit
import Foundation

/// Captures the general pasteboard by polling changeCount (0.3s — the only
/// supported observation mechanism on macOS). String payloads only for now.
/// LOCAL-ONLY BY CONSTRUCTION: this app only ever reads NSPasteboard.general
/// on this machine and never participates in any sync of its own. (Universal
/// Clipboard is a system behavior outside any app's control — the concealed
/// TTL is the mitigation there.)
final class PasteboardWatcher {
    static let concealedType = NSPasteboard.PasteboardType("org.nspasteboard.ConcealedType")
    static let transientType = NSPasteboard.PasteboardType("org.nspasteboard.TransientType")

    private var timer: Timer?
    private var lastChangeCount: Int
    private var ignoreCount = 0
    private let store: HistoryStore

    init(store: HistoryStore) {
        self.store = store
        self.lastChangeCount = NSPasteboard.general.changeCount
    }

    func start() {
        timer = Timer.scheduledTimer(withTimeInterval: 0.3, repeats: true) { [weak self] _ in
            self?.poll()
        }
    }

    /// Call before this app writes the pasteboard itself (copy-back), so the
    /// write is not re-captured as a new entry.
    func ignoreNextChange() {
        ignoreCount += 1
    }

    private func poll() {
        let pb = NSPasteboard.general
        guard pb.changeCount != lastChangeCount else { return }
        lastChangeCount = pb.changeCount
        if ignoreCount > 0 {
            ignoreCount -= 1
            return
        }
        let types = pb.types ?? []
        if types.contains(Self.transientType) { return } // honor the convention: don't record
        guard let value = pb.string(forType: .string), !value.isEmpty else { return }
        let concealed = types.contains(Self.concealedType)
        store.add(value: value, concealed: concealed)
    }
}
