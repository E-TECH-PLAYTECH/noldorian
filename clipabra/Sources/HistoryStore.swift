import AppKit
import Combine
import Foundation

/// Ring of the last 50 captures. Persistence policy (LOCKED):
///   - normal entries persist to history.json (0600) and survive relaunch;
///   - concealed entries are MEMORY-ONLY with a 5-minute TTL, then wiped
///     (removed from the ring, audit row "wipe"). They are never written to disk.
final class HistoryStore: ObservableObject {
    static let maxEntries = 50
    static let concealedTTL: TimeInterval = 300

    @Published private(set) var entries: [ClipEntry] = []

    private let persistFile = AuditLog.dir.appendingPathComponent("history.json")

    init() {
        load()
    }

    func add(value: String, concealed: Bool) {
        if let newest = entries.first, newest.value == value { return } // dedupe consecutive
        let entry = ClipEntry(value: value, concealed: concealed)
        entries.insert(entry, at: 0)
        if entries.count > Self.maxEntries { entries.removeLast(entries.count - Self.maxEntries) }
        AuditLog.append(event: "capture", entry: entry)
        if concealed {
            DispatchQueue.main.asyncAfter(deadline: .now() + Self.concealedTTL) { [weak self] in
                self?.wipe(id: entry.id)
            }
        } else {
            persist()
        }
    }

    func wipe(id: UUID) {
        guard let idx = entries.firstIndex(where: { $0.id == id }) else { return }
        AuditLog.append(event: "wipe", entry: entries[idx])
        entries.remove(at: idx)
    }

    /// Copy an entry back to the pasteboard. Concealed entries go back out with
    /// org.nspasteboard.ConcealedType so downstream managers skip them too.
    func copyBack(_ entry: ClipEntry, watcher: PasteboardWatcher) {
        guard let v = entry.value else { return }
        let pb = NSPasteboard.general
        pb.clearContents()
        if entry.concealed {
            pb.setString(v, forType: NSPasteboard.PasteboardType("org.nspasteboard.ConcealedType"))
        }
        pb.setString(v, forType: .string)
        watcher.ignoreNextChange()
        AuditLog.append(event: "copyback", entry: entry)
    }

    // MARK: persistence (normal entries only)

    private func persist() {
        let normal = entries.filter { !$0.concealed }
        guard let data = try? JSONEncoder().encode(normal) else { return }
        try? FileManager.default.createDirectory(at: AuditLog.dir, withIntermediateDirectories: true,
                                                 attributes: [.posixPermissions: 0o700])
        try? data.write(to: persistFile)
        try? FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: persistFile.path)
    }

    private func load() {
        guard let data = try? Data(contentsOf: persistFile),
              let saved = try? JSONDecoder().decode([ClipEntry].self, from: data) else { return }
        entries = Array(saved.prefix(Self.maxEntries))
    }
}
