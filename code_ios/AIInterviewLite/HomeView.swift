import SwiftUI

struct HomeView: View {
    @EnvironmentObject private var authStore: AuthStore
    @EnvironmentObject private var router: AppRouter

    private let columns = [
        GridItem(.adaptive(minimum: 152), spacing: 12)
    ]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    HomeHero(name: authStore.user?.name ?? "同学")

                    LazyVGrid(columns: columns, spacing: 12) {
                        ForEach(AgentIntent.allCases) { intent in
                            Button {
                                router.openShortcut(intent)
                            } label: {
                                ShortcutCard(intent: intent)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .padding(16)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("智能助手")
        }
    }
}

struct HomeHero: View {
    let name: String

    var body: some View {
        ZStack(alignment: .leading) {
            TechSignalPanel()
            VStack(alignment: .leading, spacing: 10) {
                Text("你好，\(name)")
                    .font(.title.bold())
                    .foregroundStyle(.white)
                Text("粘贴材料，后端 IntentRouter 会自动分发 Agent。")
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.78))
                    .fixedSize(horizontal: false, vertical: true)
                HStack(spacing: 8) {
                    Label("纯文字", systemImage: "text.alignleft")
                    Label("统一入口", systemImage: "arrow.triangle.branch")
                }
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white.opacity(0.86))
            }
            .padding(20)
        }
    }
}

struct ShortcutCard: View {
    let intent: AgentIntent

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Image(systemName: intent.symbolName)
                .font(.system(size: 24, weight: .semibold))
                .frame(width: 42, height: 42)
                .foregroundStyle(Color.intentTint(intent.tintName))
                .background(Color.intentTint(intent.tintName).opacity(0.14), in: RoundedRectangle(cornerRadius: 8, style: .continuous))

            VStack(alignment: .leading, spacing: 4) {
                Text(intent.title)
                    .font(.headline)
                    .foregroundStyle(.primary)
                    .lineLimit(1)
                    .minimumScaleFactor(0.82)
                Text(intent.subtitle)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, minHeight: 132, alignment: .topLeading)
        .padding(14)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(Color(.separator).opacity(0.35), lineWidth: 0.5)
        )
    }
}

struct TechSignalPanel: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var compact = false

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30.0)) { timeline in
            let time = reduceMotion ? 0 : timeline.date.timeIntervalSinceReferenceDate
            Canvas { context, size in
                let progress = reduceMotion ? 0.48 : time.truncatingRemainder(dividingBy: 4.0) / 4.0
                let gridColor = Color.white.opacity(0.12)
                let accent = Color.cyan.opacity(0.72)
                let scanX = size.width * progress

                for index in 1...4 {
                    let y = size.height * CGFloat(index) / 5.0
                    var path = Path()
                    path.move(to: CGPoint(x: 18, y: y))
                    path.addLine(to: CGPoint(x: size.width - 18, y: y))
                    context.stroke(path, with: .color(gridColor), lineWidth: 1)
                }

                for index in 1...5 {
                    let x = size.width * CGFloat(index) / 6.0
                    var path = Path()
                    path.move(to: CGPoint(x: x, y: 16))
                    path.addLine(to: CGPoint(x: x, y: size.height - 16))
                    context.stroke(path, with: .color(gridColor), lineWidth: 1)
                }

                var signal = Path()
                signal.move(to: CGPoint(x: 26, y: size.height * 0.68))
                signal.addLine(to: CGPoint(x: size.width * 0.32, y: size.height * 0.42))
                signal.addLine(to: CGPoint(x: size.width * 0.58, y: size.height * 0.56))
                signal.addLine(to: CGPoint(x: size.width - 28, y: size.height * 0.28))
                context.stroke(signal, with: .color(.white.opacity(0.34)), lineWidth: 2)

                var scan = Path()
                scan.move(to: CGPoint(x: scanX, y: 0))
                scan.addLine(to: CGPoint(x: scanX, y: size.height))
                context.stroke(scan, with: .color(accent), lineWidth: 2)

                for point in [
                    CGPoint(x: size.width * 0.32, y: size.height * 0.42),
                    CGPoint(x: size.width * 0.58, y: size.height * 0.56),
                    CGPoint(x: size.width - 28, y: size.height * 0.28)
                ] {
                    let rect = CGRect(x: point.x - 4, y: point.y - 4, width: 8, height: 8)
                    context.fill(Path(ellipseIn: rect), with: .color(.white.opacity(0.82)))
                }
            }
        }
        .frame(height: compact ? 156 : 176)
        .background(
            LinearGradient(
                colors: [Color(red: 0.02, green: 0.08, blue: 0.18), Color(red: 0.02, green: 0.34, blue: 0.55)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 8, style: .continuous)
        )
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(Color.white.opacity(0.12), lineWidth: 1)
        )
    }
}

extension Color {
    static func intentTint(_ name: String) -> Color {
        switch name {
        case "blue": return .blue
        case "teal": return .teal
        case "indigo": return .indigo
        case "green": return .green
        case "orange": return .orange
        case "pink": return .pink
        default: return .accentColor
        }
    }
}
