# Product Editions And Directory Contract

Last updated: 2026-07-03

This document is the authoritative contract for product versions and packaging boundaries.

## Product Direction

The primary product is a native iOS app for counselors, distributed through TestFlight and the Apple App Store. The Web workbench and Coze plugin remain useful compatibility and market-validation surfaces, but neither is the App Store deliverable.

## Version Semantics

| Name | Meaning | Current value |
|---|---|---|
| Product phase | Human-facing delivery stage | App Store Release Candidate |
| iOS marketing version | `CFBundleShortVersionString` shown in App Store | `1.0.0` |
| iOS build number | `CFBundleVersion`; increment for each upload | `1` |
| API contract version | Server/client compatibility contract | explicit endpoint/schema version, independent of app version |
| `v0.1` / `0.1.0` / `MVP` | Historical filenames, schemas, eval assets, and compatibility paths | legacy only; not the current product version |

Do not rename a legacy file merely to make its name look current when code reads that exact path. Add a compatibility note instead, and migrate references deliberately with tests.

## Directory Ownership

### `ios-app/` - App Store package root

Allowed:

- Swift/SwiftUI source
- Xcode/XcodeGen project metadata
- app icons, launch assets, localized strings
- `Info.plist`, entitlements, privacy manifest
- iOS unit/UI tests
- App Store metadata and release scripts that contain no credentials

Forbidden:

- `.env` files or API keys
- DeepSeek credentials or direct model-provider calls
- Python runtime and server scripts
- full RAG/source-card content
- Web workbench assets copied as the product UI
- Coze plugin schemas or Render deployment files
- real counseling records, uploaded templates, or generated runtime artifacts

### `web-workbench/` - retained Web client

This remains a browser-based validation and fallback surface. It can exercise shared API capabilities but is not embedded in the iOS archive and does not define App Store readiness.

### `scripts/` - shared service and engineering tools

This owns the hosted API, agent runtime, retrieval, document generation, eval runners, Web host, and Coze adapter. iOS consumes a stable HTTPS product API exposed by this layer.

### Coze and Render files - retained adapters/deployment

`docs/coze-*`, Coze routes, OpenAPI compatibility files, and `render.yaml` remain available for the existing integration. They are operational infrastructure, not iOS resources.

### Runtime data directories

`agent-runs/`, `workbench-data/`, `eval-results/api/`, local logs, and uploaded documents are never app resources and must remain ignored or fixture-only.

## App Architecture Boundary

The iOS app is a thin trusted client:

1. It collects de-identified counselor input and user intent.
2. It authenticates to the product backend.
3. The backend performs routing, RAG retrieval, model calls, validation, document generation, and audit handling.
4. The app renders structured results and downloads/shares approved artifacts.

No model-provider secret is stored in the app. Server responses must remain reviewable and must not present agent output as diagnosis, final risk classification, or a replacement for professional judgment.

## App Store Completion Gates

- Native app target builds and tests on a supported Xcode version.
- Core counselor journey passes on at least one current iPhone simulator and one physical-device/TestFlight build.
- Release archive contains only iOS target resources and passes package-boundary validation.
- App privacy manifest, privacy policy URL, support URL, age rating, export-compliance answers, screenshots, and review notes are ready.
- Account creation/deletion and data-retention behavior match the production service.
- Production HTTPS API, authentication, file transfer, and all P0 agent capabilities pass acceptance tests.
- No secrets or identifiable counseling data are present in source control, archive, logs, screenshots, or App Store metadata.

## Source Of Truth Order

When documents conflict, use this order:

1. `docs/product-loop-state.md` for current work and next priority.
2. This file for product/version/directory boundaries.
3. Current API schemas and executable tests for runtime contracts.
4. Legacy `v0.1`/MVP documents for historical behavior only.
