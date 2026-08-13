import SwiftUI

struct LoginView: View {
    @EnvironmentObject private var session: SessionStore
    @State private var username = ""
    @State private var password = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("工作区账号", text: $username)
                        .textContentType(.username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    SecureField("密码", text: $password)
                        .textContentType(.password)
                } header: {
                    Text("登录咨询师工作区")
                } footer: {
                    Text("请使用去标识化编号，不要把姓名、电话、证件号码等直接身份信息录入个案材料。")
                }

                if let message = session.errorMessage {
                    Section {
                        Text(message)
                            .foregroundStyle(.red)
                            .accessibilityLabel("登录错误：\(message)")
                    }
                }

                Button {
                    Task { await session.signIn(username: username, password: password) }
                } label: {
                    HStack {
                        Spacer()
                        if session.isWorking {
                            ProgressView()
                        } else {
                            Text("登录")
                        }
                        Spacer()
                    }
                }
                .disabled(username.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || password.isEmpty || session.isWorking)
            }
            .navigationTitle("咨询师助理")
        }
    }
}
