# Product Editions And Directory Contract

Last updated: 2026-08-14

This document is the authoritative contract for product versions and packaging boundaries.

## Product Direction

The supported product surfaces are the native iOS app for counselors, distributed through TestFlight and the Apple App Store, and the independent hosted Web/API service. The iOS app is the App Store deliverable; the Web workbench remains the browser product and service backend without entering the iOS archive.

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
- Render deployment files or other server configuration
- real counseling records, uploaded templates, or generated runtime artifacts

### `web-workbench/` - hosted Web product

This is the browser client for the independent hosted Web/API service. It exercises the same server-side capabilities used by iOS but is not embedded in the iOS archive and does not define App Store readiness.

### `scripts/` - shared service and engineering tools

This owns the single hosted API, agent runtime, retrieval, document generation, eval runners, and Web host. iOS consumes a stable HTTPS product API exposed by this layer.

### `render.yaml` - single-service deployment

`render.yaml` deploys only the independent `counselor-agent-web` service. Deployment configuration is operational infrastructure, not an iOS resource.

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
