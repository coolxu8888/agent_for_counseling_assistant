import SwiftUI
import QuickLook

private enum ResultTab: String, CaseIterable, Identifiable {
    case output = "输出"
    case structured = "结构"
    case safety = "校验"

    var id: String { rawValue }
}

struct CaseDetailView: View {
    @EnvironmentObject private var session: SessionStore
    @Environment(\.dismiss) private var dismiss
    let counselorCase: CounselorCase

    @State private var material = ""
    @State private var result: AgentRunResponse?
    @State private var recentRuns: [RecentRun] = []
    @State private var selectedTab: ResultTab = .output
    @State private var isRunning = false
    @State private var errorMessage: String?
    @State private var showingDeleteConfirmation = false
    @State private var previewURL: URL?
    @State private var downloadedArtifacts: [String: URL] = [:]
    @State private var loadingRunID: String?
    @State private var loadingArtifactKey: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                caseHeader
                materialComposer
                if let result {
                    resultView(result)
                } else if !recentRuns.isEmpty {
                    recentHistory
                }
            }
            .padding()
        }
        .navigationTitle(counselorCase.title)
        .navigationBarTitleDisplayMode(.inline)
        .task { await loadDetail() }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button("删除个案", systemImage: "trash", role: .destructive) {
                        showingDeleteConfirmation = true
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
                .accessibilityLabel("个案操作")
            }
        }
        .alert("删除这个个案？", isPresented: $showingDeleteConfirmation) {
            Button("取消", role: .cancel) {}
            Button("删除", role: .destructive) {
                Task {
                    if await session.deleteCase(id: counselorCase.id) {
                        dismiss()
                    } else {
                        errorMessage = session.errorMessage
                    }
                }
            }
        } message: {
            Text("相关上传、运行记录和审计数据会一并删除，此操作不可撤销。")
        }
        .quickLookPreview($previewURL)
    }

    private var caseHeader: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("当前个案")
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(counselorCase.clientCode.isEmpty ? "未设置来访编号" : counselorCase.clientCode)
                .font(.headline)
            Text("系统会自动判断是初访、个案整理、咨询记录、概念化或方案任务。")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
    }

    private var materialComposer: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("咨询师材料").font(.headline)
            TextEditor(text: $material)
                .frame(minHeight: 180)
                .padding(8)
                .background(Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
                .accessibilityLabel("咨询师材料")
            Text("提交前请删除姓名、电话、证件号、精确住址等直接身份信息。")
                .font(.caption)
                .foregroundStyle(.secondary)

            if let errorMessage {
                Text(errorMessage).foregroundStyle(.red)
            }

            Button {
                Task { await run() }
            } label: {
                HStack {
                    Spacer()
                    if isRunning { ProgressView() } else { Text("整理材料") }
                    Spacer()
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(material.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isRunning)
        }
    }

    @ViewBuilder
    private func resultView(_ result: AgentRunResponse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(result.detectedWorkflowLabel)
                .font(.headline)
            if let notice = result.routeNotice, !notice.isEmpty {
                Text(notice)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
            Picker("结果内容", selection: $selectedTab) {
                ForEach(ResultTab.allCases) { tab in
                    Text(tab.rawValue).tag(tab)
                }
            }
            .pickerStyle(.segmented)

            Group {
                switch selectedTab {
                case .output:
                    Text(result.cleanOutput)
                case .structured:
                    Text(result.structuredOutput?.prettyPrinted ?? "本次没有结构化结果。")
                        .font(.system(.footnote, design: .monospaced))
                case .safety:
                    Text(result.safetyCheck?.prettyPrinted ?? result.structuredCheck?.prettyPrinted ?? "本次没有额外校验结果。")
                        .font(.system(.footnote, design: .monospaced))
                }
            }
            .textSelection(.enabled)

            if !result.artifacts.isEmpty {
                Divider()
                Text("文档").font(.headline)
                ForEach(result.artifacts) { artifact in
                    HStack {
                        Label(artifact.name, systemImage: "doc.text")
                        Spacer()
                        if loadingArtifactKey == artifact.key {
                            ProgressView()
                        } else {
                            Button("预览") {
                                Task { await preview(artifact) }
                            }
                        }
                        if let url = downloadedArtifacts[artifact.key] {
                            ShareLink(item: url) {
                                Image(systemName: "square.and.arrow.up")
                            }
                            .accessibilityLabel("分享 \(artifact.name)")
                        }
                    }
                }
            }
        }
    }

    private var recentHistory: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("近期记录").font(.headline)
            ForEach(recentRuns.prefix(5)) { run in
                Button {
                    Task { await reopen(run) }
                } label: {
                    HStack {
                        Text(run.workflow.isEmpty ? "历史记录" : run.workflow)
                        Spacer()
                        if loadingRunID == run.runID {
                            ProgressView()
                        } else {
                            Image(systemName: "chevron.right")
                                .foregroundStyle(.tertiary)
                        }
                    }
                }
                .buttonStyle(.plain)
                .disabled(loadingRunID != nil)
            }
        }
    }

    private func loadDetail() async {
        do {
            let detail = try await session.caseDetail(id: counselorCase.id)
            recentRuns = detail.recentRuns
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func run() async {
        isRunning = true
        errorMessage = nil
        defer { isRunning = false }
        do {
            result = try await session.runAgent(caseID: counselorCase.id, input: material)
            selectedTab = .output
            await loadDetail()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func reopen(_ run: RecentRun) async {
        loadingRunID = run.runID
        errorMessage = nil
        defer { loadingRunID = nil }
        do {
            result = try await session.runDetail(runID: run.runID)
            selectedTab = .output
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func preview(_ artifact: RunArtifact) async {
        loadingArtifactKey = artifact.key
        errorMessage = nil
        defer { loadingArtifactKey = nil }
        do {
            let url = try await session.downloadArtifact(artifact)
            downloadedArtifacts[artifact.key] = url
            previewURL = url
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
