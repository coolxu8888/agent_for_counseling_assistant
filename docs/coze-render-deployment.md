# Coze Demo API Render Deployment

## Goal

Deploy the Coze demo API as an HTTPS service so Coze can import `/openapi.json` and call:

- `run_workflow`
- `draft_template`

## Current Local Services

- Web MVP UI: `http://127.0.0.1:8765`
- Coze demo API: `http://127.0.0.1:8770`

Coze cannot call `127.0.0.1`, so the API needs a public or intranet HTTPS URL.

## Files Added

- `render.yaml`: Render Blueprint for the Coze API service.
- `requirements.txt`: Python dependency list.
- `runtime.txt`: Python runtime pin.
- `docs/coze-openapi.json`: static OpenAPI draft.
- `docs/coze-openapi.coze-min.json`: compact OpenAPI schema for Coze import troubleshooting.
- `docs/coze-openapi.swagger2.json`: Swagger 2.0 fallback for Coze importers that reject OpenAPI 3 URL prefixes.

## Required Environment Variables

Set these in Render:

- `DEEPSEEK_API_KEY`: DeepSeek API key.
- `COZE_DEMO_API_KEY`: any strong random string used by Coze when calling tools.
- `WORKBENCH_USER`: operator or fallback demo username for the hosted Web MVP.
- `WORKBENCH_PASSWORD`: operator or fallback demo password for the hosted Web MVP.

Optional defaults are already in `render.yaml`:

- `DEEPSEEK_BASE_URL=https://api.deepseek.com`
- `DEEPSEEK_MODEL=deepseek-v4-flash`
- `DEEPSEEK_TIMEOUT_SECONDS=120`
- `WORKBENCH_ALLOW_SIGNUP=false`

Optional pilot auth controls:

- `WORKBENCH_ALLOW_SIGNUP=true`: allow counselors to create their own isolated workspaces from the login screen.
- `WORKBENCH_SIGNUP_INVITE_CODE=<strong random string>`: require the invite code during signup. Recommended whenever signup is enabled.
- `WORKBENCH_MAX_UPLOAD_BYTES=10485760`: per-file upload limit for hosted templates and materials.
- `WORKBENCH_RETENTION_DAYS=14`: enables one-click pruning of uploads, saved runs, and audit activity older than the retention window.

## Deploy Steps

1. Push this repository to GitHub, GitLab, or Bitbucket.
2. Open Render Dashboard.
3. Create a Blueprint from the pushed repository.
4. Render reads `render.yaml` and creates `counselor-agent-coze-api`.
5. Fill `DEEPSEEK_API_KEY` and `COZE_DEMO_API_KEY`.
6. For pilot access, either keep a single shared login with `WORKBENCH_USER` / `WORKBENCH_PASSWORD`, or enable isolated workspaces with `WORKBENCH_ALLOW_SIGNUP=true` and `WORKBENCH_SIGNUP_INVITE_CODE`.
7. Set `WORKBENCH_MAX_UPLOAD_BYTES` and `WORKBENCH_RETENTION_DAYS` to the policy you want to validate in the hosted MVP.
8. Deploy.
9. Confirm:

```text
https://<render-service>.onrender.com/health
https://<render-service>.onrender.com/openapi.json
```

Expected health response:

```json
{"status":"ok"}
```

For an operator-focused hosted product check after deploy, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-hosted-smoke.ps1 `
  -BaseUrl https://<render-service>.onrender.com `
  -Username <operator-user> `
  -Password <operator-password> `
  -ExpectPilotReady `
  -RealRun
```

If signup is enabled for isolated counselor workspaces, prefer validating with a fresh signup account:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-hosted-smoke.ps1 `
  -BaseUrl https://<render-service>.onrender.com `
  -Username pilot-user-001 `
  -Password <new-password> `
  -InviteCode <invite-code> `
  -RequireSignup `
  -ExpectPilotReady `
  -RealRun
```

## Coze Tool Setup

After deployment:

1. In Coze, create a plugin/tool from OpenAPI.
2. Use:

```text
https://<render-service>.onrender.com/openapi.json
```

3. Configure header authentication:

```text
X-API-Key: <COZE_DEMO_API_KEY>
```

4. Enable these operations:

- `run_workflow`
- `draft_template`

If Coze imports tools such as `get_list` or `retrieve` with knowledge-base
connector parameters, the wrong connector/plugin type was imported. Re-import
the deployed `/openapi.json` URL or paste `docs/coze-openapi.coze-min.json` as
raw OpenAPI data. The expected tool names are only `run_workflow` and
`draft_template`.

If Coze reports `Inconsistent API URL prefix`, upload
`docs/coze-openapi.swagger2.json` instead. The Swagger 2.0 schema uses
`host=counselor-agent-coze-api.onrender.com`, `basePath=/coze`, and relative
paths `/run_workflow` and `/draft_template`, which keeps the API prefix explicit.

## Demo Notes

For `draft_template`, deployed demos should prefer:

- `template_base64`
- `template_filename`

Do not rely on Windows local paths such as `C:\Users\...\template.docx` after deployment. Those paths only work on the local machine.

## Known Limitations

- Render free instances may sleep, causing the first request to be slow.
- Generated files live on ephemeral service storage. This is acceptable for a demo but not for production case storage.
- Storage is still local to the service instance, so workspace data is not durable across rebuilds or instance loss.
- Upload limits and retention pruning now exist for the hosted MVP, but production still needs durable object storage, encrypted secrets/storage, and a stronger server-side data lifecycle architecture.
