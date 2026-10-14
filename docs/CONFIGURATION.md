# Configuration and troubleshooting

[Back to README](../README.md)

## Environment variables

### Frontend: `frontend/.env.local`

| Variable | Purpose |
| --- | --- |
| `VITE_API_URL` | Locally `http://localhost:8000`. Leave unset on Vercel to use same-origin `/api`. |
| `VITE_SUPABASE_URL` | Optional: your Supabase project URL. |
| `VITE_SUPABASE_ANON_KEY` | Optional: your project's publishable/anon key. Never a service-role key. |

### Backend: `backend/.env`

| Variable | Purpose |
| --- | --- |
| `OPENROUTER_API_KEY` | Optional private key enabling chat. Keep it on the backend only. |
| `OPENROUTER_MODEL` | Model identifier; defaults to `openrouter/auto`. |
| `SITE_URL` | Frontend URL used for provider attribution. |
| `CORS_ORIGINS` | Comma-separated exact frontend origins allowed to read API responses. |

Use your own provider projects and keys. All `VITE_*` settings are public in the browser bundle. Both local environment files are ignored by Git. Restart the corresponding server after changes; frontend production changes require a rebuild.

If OpenRouter is unset, chat returns a friendly unavailable message. If Supabase is unset, feedback cannot be submitted. Setting Supabase keys alone does not create the database: configure the `feedback` table with `name`, `email`, `rating`, `message`, `ip`, and `location` columns and appropriate insert-only RLS permissions. Do not enable public reads of submitted personal data.

The chat proxy has bounded inputs, a response-token limit, a timeout, and a per-process, per-IP rate limit. CORS is not authentication. Before operating a public paid chat service at scale, configure a provider spending limit and durable abuse controls; in-memory limits reset on restart and are not shared across workers.

## Validation

```powershell
npm --prefix frontend run build
npm --prefix frontend audit
.\.venv\Scripts\python.exe -m pip check
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m unittest discover -s backend -p "test_*.py" -v
Invoke-RestMethod http://127.0.0.1:8000/health
```

The API tests use the real model and mock OpenRouter responses; they do not spend provider credits or write feedback records.

## Troubleshooting

- **Invalid `VITE_API_URL`:** use `/api` on Vercel or an HTTPS URL for a separately hosted backend.
- **CORS errors:** add the exact frontend origin to backend `CORS_ORIGINS`, then restart the backend.
- **Connection refused / failed to fetch:** start FastAPI on port 8000 and check `/health`; never use localhost as the API URL for a live site.
- **Model import/version errors:** install the constrained Python dependencies and confirm all three artifacts exist.
- **Unicode errors in Windows:** set `$env:PYTHONUTF8 = "1"` before starting Python.
- **Chat unavailable:** configure `OPENROUTER_API_KEY` in the backend and verify provider access/credits. Never reintroduce a browser-side key.
- **Feedback unavailable:** configure your Supabase project, table, grants, and RLS.
- **NOAA unavailable:** historical charts remain usable; live results depend on the upstream service.
- **Port 5173 occupied:** stop the other development server; this project uses a fixed port to keep CORS settings consistent.
