import Foundation

/// One clipboard capture. `value` is nil after a concealed entry's TTL wipe.
struct ClipEntry: Identifiable, Codable, Equatable {
    let id: UUID
    let capturedAt: Date
    var value: String?
    let length: Int
    let concealed: Bool

    init(value: String, concealed: Bool) {
        self.id = UUID()
        self.capturedAt = Date()
        self.value = value
        self.length = value.count
        self.concealed = concealed
    }

    /// Single-line list preview. Concealed entries never preview content.
    var preview: String {
        guard !concealed else { return "concealed · \(length) chars" }
        guard let v = value else { return "(wiped) · \(length) chars" }
        let oneLine = v.replacingOccurrences(of: "\n", with: " ⏎ ")
        return oneLine.count > 60 ? String(oneLine.prefix(60)) + "…" : oneLine
    }
}
