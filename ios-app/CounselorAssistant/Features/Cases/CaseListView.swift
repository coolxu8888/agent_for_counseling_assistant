import SwiftUI

struct CaseListView: View {
    @EnvironmentObject private var session: SessionStore
    @State private var showingCreateCase = false

    var body: some View {
        NavigationStack {
            Group {
                if session.cases.isEmpty {
                    ContentUnavailableView(
                        "暂无个案",
                        systemImage: "person.text.rectangle",
                        description: Text("后续步骤将在这里创建仅使用去标识化编号的个案。")
                    )
                } else {
                    List(session.cases) { item in
                        NavigationLink {
                            CaseDetailView(counselorCase: item)
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(item.title)
                                    .font(.headline)
                                if !item.clientCode.isEmpty {
                                    Text(item.clientCode)
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .accessibilityElement(children: .combine)
                        }
                    }
                    .refreshable { await session.refreshCases() }
                }
            }
            .navigationTitle("去标识化个案")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("新建个案", systemImage: "plus") {
                        showingCreateCase = true
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("退出", systemImage: "rectangle.portrait.and.arrow.right") {
                        Task { await session.signOut() }
                    }
                }
            }
            .sheet(isPresented: $showingCreateCase) {
                CreateCaseView()
            }
            .safeAreaInset(edge: .bottom) {
                Text("Agent 输出不替代咨询师的专业判断或风险处置。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 8)
            }
        }
    }
}
