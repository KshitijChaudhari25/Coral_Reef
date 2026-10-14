# Deployment

[Back to README](../README.md)

- **Production:** https://coral-reef-lake.vercel.app
- **Repository:** https://github.com/KshitijChaudhari25/Coral_Reef
- **Vercel project:** `coral-reef`, in the `kshitij-7a8f` team

## How it works

The repository root contains `vercel.json`. Vercel Services (currently beta) builds `frontend/` with Vite and `backend/` with FastAPI. Public requests under `/api/*` go to the backend, where FastAPI explicitly mounts `/api`. Other requests go to the frontend. Both services share one domain, including on preview deployments.

Keep the Vercel project root at the repository root, not `frontend/`. Service-specific build settings are already in `vercel.json`.

## Publish changes

From the repository root, review and commit the files you changed:

```powershell
git status
git add .
git diff --cached --stat
git commit -m "Describe your change"
git push origin main
```

GitHub pushes to `main` trigger production deployment automatically. Check the deployment status in Vercel before considering the release complete.

## Environment variables

Open the Vercel project, then **Settings → Environment Variables**. Choose Production and/or Preview as appropriate, save, and redeploy.

| Variable | When to set it |
| --- | --- |
| `VITE_API_URL` | Leave unset; production defaults to `/api`. Never use localhost here. |
| `VITE_SUPABASE_URL` | Enable feedback with your Supabase project URL. |
| `VITE_SUPABASE_ANON_KEY` | Public anon/publishable key; configure table grants and RLS first. |
| `OPENROUTER_API_KEY` | Private/sensitive value enabling the assistant. Never use a `VITE_` prefix. |
| `OPENROUTER_MODEL` | Optional model override; defaults to `openrouter/auto`. |
| `SITE_URL` | Production frontend URL used for OpenRouter attribution. |
| `CORS_ORIGINS` | Only needed for additional cross-origin frontends you intentionally allow. |

See [configuration](CONFIGURATION.md) for local settings and feedback-table requirements.

## Verify a release

1. Check `/api/health` returns `status: ok`.
2. Open the dashboard and confirm historical charts and the map load.
3. Run a prediction, then a scenario simulation.
4. Check satellite status; an upstream outage should show historical fallback.
5. Test chat and feedback only after configuring their providers.

## Known deployment fixes

- Python dependencies are pinned directly in `backend/requirements.txt`. Avoid nested constraints includes: Vercel failed to parse one during the initial deployment.
- Python version is selected by `backend/.python-version`; model artifacts require the pinned scikit-learn version.
- The trained model is about 92.3 MiB. Keep it included, and investigate actual bundle-size errors before removing artifacts.
- API routes must retain the FastAPI `/api` mount. A service routing destination alone did not strip that prefix at runtime.
- A Vite bundle-size warning is not a failed build.

## Alternative backend hosting

`deployment/render.yaml` is an optional Render blueprint. If using Render, select that blueprint path and retain its backend root directory. Set `VITE_API_URL` to the hosted backend's HTTPS URL and configure backend CORS for the frontend origin. The current production site uses Vercel for both services.
