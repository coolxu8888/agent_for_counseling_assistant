import SwiftUI

struct CreateCaseView: View {
    @EnvironmentObject private var session: SessionStore
    @Environment(\.dismiss) private var dismiss
    @State private var title = ""
    @State private var clientCode = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("个案标题，例如：初访-A001", text: $title)
                    TextField("来访编号，例如：A001", text: $clientCode)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled()
                } header: {
                    Text("去标识化个案")
                } footer: {
                    Text("仅使用内部编号或不可直接识别身份的标题，不填写姓名、电话、证件号或具体单位。")
                }

                if let message = session.errorMessage {
                    Text(message).foregroundStyle(.red)
                }
            }
            .navigationTitle("新建个案")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("创建") {
                        Task {
                            if await session.createCase(title: title, clientCode: clientCode) {
                                dismiss()
                            }
                        }
                    }
                    .disabled(title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || session.isWorking)
                }
            }
        }
    }
}
