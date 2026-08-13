# Counselor Assistant iOS

This directory is the only App Store application root.

## Release identity

- Product phase: App Store Release Candidate
- Marketing version: `1.0.0`
- Build number: `1`
- Bundle identifier placeholder: `com.counselorassistant.app`

Set the final Apple Developer team and bundle identifier in `Config/Release.xcconfig` before signing. Never place service or model API keys in an xcconfig, plist, Swift source file, or asset catalog.

## Project generation

The project is described by `project.yml` so generated Xcode files remain reproducible. On macOS with XcodeGen installed:

```bash
cd ios-app
xcodegen generate
open CounselorAssistant.xcodeproj
```

The native app calls the hosted product API. Web assets, Python code, RAG source cards, Coze files, `.env`, and local run data are intentionally outside the target.

## Mobile API contract

The native client uses `/api/mobile/v1`:

- `POST /login`
- `GET /session`
- `POST /logout`
- `GET /cases`
- `POST /cases`
- `GET /cases/{id}`
- `POST /runs` (always server-side `AUTO` routing)
- `GET /runs/{run_id}` (opaque history reopen)
- `GET /runs/{run_id}/artifacts/{artifact_key}` (authenticated whitelist download)

Authentication uses a workspace bearer session stored in the iOS Keychain. The model-provider key remains server-side. The Web cookie endpoints and Coze plugin routes are separate compatibility surfaces.

## Validation

From the repository root on Windows or macOS:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ios-app/scripts/validate-package-boundary.ps1
```

On a macOS/Xcode runner, generate the project, run unit/UI tests, run a simulator acceptance journey, then create and validate a signed archive. A Windows package-boundary check is necessary but does not prove App Store readiness.
