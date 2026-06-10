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

## Required Environment Variables

Set these in Render:

- `DEEPSEEK_API_KEY`: DeepSeek API key.
- `COZE_DEMO_API_KEY`: any strong random string used by Coze when calling tools.

Optional defaults are already in `render.yaml`:

- `DEEPSEEK_BASE_URL=https://api.deepseek.com`
- `DEEPSEEK_MODEL=deepseek-v4-flash`
- `DEEPSEEK_TIMEOUT_SECONDS=120`

## Deploy Steps

1. Push this repository to GitHub, GitLab, or Bitbucket.
2. Open Render Dashboard.
3. Create a Blueprint from the pushed repository.
4. Render reads `render.yaml` and creates `counselor-agent-coze-api`.
5. Fill `DEEPSEEK_API_KEY` and `COZE_DEMO_API_KEY`.
6. Deploy.
7. Confirm:

```text
https://<render-service>.onrender.com/health
https://<render-service>.onrender.com/openapi.json
```

Expected health response:

```json
{"status":"ok"}
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

## Demo Notes

For `draft_template`, deployed demos should prefer:

- `template_base64`
- `template_filename`

Do not rely on Windows local paths such as `C:\Users\...\template.docx` after deployment. Those paths only work on the local machine.

## Known Limitations

- Render free instances may sleep, causing the first request to be slow.
- Generated files live on ephemeral service storage. This is acceptable for a demo but not for production case storage.
- Production needs account auth, durable object storage, upload size limits by user, audit logging, and stricter data retention controls.
