import SwiftUI

/// Masked history list + chord-gated reveal pane.
/// - Normal entries: 60-char single-line preview in the list.
/// - Concealed entries: "concealed · N chars" — never previewed.
/// - The detail pane shows the SELECTED entry's full value ONLY while the
///   4+7 reveal chord is held (PanelState.revealHeld); otherwise a mask.
struct HistoryView: View {
    @ObservedObject var store: HistoryStore
    @ObservedObject var state: PanelState
    let onCopyBack: (ClipEntry) -> Void

    var body: some View {
        VStack(spacing: 0) {
            if store.entries.isEmpty {
                Spacer()
                Text("Nothing captured yet — copy something.")
                    .foregroundStyle(.secondary)
                Spacer()
            } else {
                List(store.entries, selection: $state.selectedID) { entry in
                    row(entry)
                        .tag(entry.id)
                        .contentShape(Rectangle())
                        .onTapGesture(count: 2) { onCopyBack(entry) }
                        .onTapGesture { state.selectedID = entry.id }
                }
                .listStyle(.inset)
                Divider()
                detailPane
            }
            Divider()
            footer
        }
        .frame(minWidth: 420, minHeight: 440)
    }

    private func row(_ entry: ClipEntry) -> some View {
        HStack(spacing: 8) {
            Image(systemName: entry.concealed ? "eye.slash" : "doc.on.clipboard")
                .foregroundStyle(entry.concealed ? .orange : .secondary)
                .frame(width: 16)
            VStack(alignment: .leading, spacing: 2) {
                Text(entry.preview)
                    .font(.system(.body, design: entry.concealed ? .default : .monospaced))
                    .lineLimit(1)
                Text(entry.capturedAt.formatted(date: .omitted, time: .standard))
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }
        }
        .padding(.vertical, 2)
    }

    @ViewBuilder
    private var detailPane: some View {
        let selected = store.entries.first { $0.id == state.selectedID }
        ScrollView {
            if let entry = selected {
                if state.revealHeld, let v = entry.value {
                    Text(v)
                        .font(.system(.body, design: .monospaced))
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(8)
                } else {
                    Text(entry.concealed
                         ? "●●●●●●●●  \(entry.length) chars — hold 4+7 to reveal"
                         : "hold 4+7 to reveal full value · double-click to copy")
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(8)
                }
            } else {
                Text("select an entry")
                    .foregroundStyle(.tertiary)
                    .padding(8)
            }
        }
        .frame(height: 120)
        .background(state.revealHeld ? Color.orange.opacity(0.08) : Color.clear)
    }

    private var footer: some View {
        HStack {
            Text("reveal: hold 4+7 · show/hide: 2+9 · double-click: copy")
                .font(.caption2)
                .foregroundStyle(.tertiary)
            Spacer()
            Text("\(store.entries.count)/\(HistoryStore.maxEntries)")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .padding(6)
    }
}
