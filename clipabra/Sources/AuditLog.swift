import CryptoKit
import Foundation

/// TULKAS-style receipts: every capture, reveal, copy-back, and wipe leaves a
/// JSONL row at ~/Library/Application Support/clipabra/audit.jsonl (0600).
/// Rows carry id / length / concealed / an 8-hex content fingerprint — NEVER
/// the value itself.
enum AuditLog {
    static let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        .appendingPathComponent("clipabra", isDirectory: true)
    static let file = dir.appendingPathComponent("audit.jsonl")

    static func append(event: String, entry: ClipEntry) {
        var row: [String: Any] = [
            "ts": ISO8601DateFormatter().string(from: Date()),
            "event": event,
            "id": entry.id.uuidString,
            "len": entry.length,
            "concealed": entry.concealed,
        ]
        if let v = entry.value {
            let digest = SHA256.hash(data: Data(v.utf8))
            row["sha256_8"] = digest.map { String(format: "%02x", $0) }.joined().prefix(8).lowercased()
        }
        guard let data = try? JSONSerialization.data(withJSONObject: row),
              let line = String(data: data, encoding: .utf8) else { return }
        write(line: line)
    }

    private static func write(line: String) {
        let fm = FileManager.default
        try? fm.createDirectory(at: dir, withIntermediateDirectories: true,
                                attributes: [.posixPermissions: 0o700])
        if !fm.fileExists(atPath: file.path) {
            fm.createFile(atPath: file.path, contents: nil,
                          attributes: [.posixPermissions: 0o600])
        }
        guard let handle = try? FileHandle(forWritingTo: file) else { return }
        defer { try? handle.close() }
        _ = try? handle.seekToEnd()
        try? handle.write(contentsOf: Data((line + "\n").utf8))
    }
}
