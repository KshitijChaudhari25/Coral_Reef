# Coral Reef Bleaching Prediction Dashboard

An interactive dashboard by **Kshitij Chaudhari** for exploring coral bleaching observations, live ocean conditions, machine-learning predictions, and climate scenarios.

Live dashboard: https://coral-reef-lake.vercel.app

Repository: https://github.com/KshitijChaudhari25/Coral_Reef

## Features

- Historical charts and an interactive Leaflet reef map.
- NOAA sea surface temperature, thermal anomalies, and degree heating weeks.
- Random Forest predictions using 13 environmental features.
- Climate scenario simulations.
- Optional Reef Assistant through a server-side OpenRouter proxy.
- Optional Supabase feedback storage, location detection, and light/dark themes.

## Stack and architecture

React 18, Vite 8, Tailwind CSS 4, Recharts, Leaflet, FastAPI, and scikit-learn.

The React frontend calls the Python API for `/health`, `/predict`, `/simulate`, `/live-data`, and `/chat`. The API holds the private OpenRouter key. Feedback uses a Supabase publishable/anon key with row-level security.

```text
src/                    React application
public/data/            Historical CSV served to the browser
backend/main.py         FastAPI endpoints
backend/predict.py      Prediction preprocessing and inference
backend/simulate.py     Scenario calculations
backend/model_files/    Trusted trained model, scaler, and feature list
backend/test_api.py     API regression tests
.env.example            Public frontend settings
backend/.env.example    Private backend settings
```

## Local setup (Windows PowerShell)

Use Node.js 24 and Python 3.14. The existing model was saved with **scikit-learn 1.9.0**; keep that version unless you retrain and validate the model. Tailwind 4 requires a modern browser (Chrome 111+, Safari 16.4+, Firefox 128+).

Run the following from the folder containing `package.json`:

```powershell
npm ci
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt -c backend/requirements-lock.txt
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

Start the backend in terminal 1:

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Start the frontend in terminal 2, from the same project folder:

```powershell
npm run dev -- --host 127.0.0.1
```

Open <http://127.0.0.1:5173>. API documentation is at <http://127.0.0.1:8000/docs>. No private API key is needed for historical charts, predictions, or simulations. NOAA access needs an internet connection.

## Environment variables

### Frontend: `.env.local`

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
npm run build
npm audit
.\.venv\Scripts\python.exe -m pip check
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m unittest discover -s backend -p "test_*.py" -v
Invoke-RestMethod http://127.0.0.1:8000/health
```

The API tests use the real model and mock OpenRouter responses; they do not spend provider credits or write feedback records.

## GitHub preparation

Commit source, `package-lock.json`, both environment templates, and the three model artifacts. Do not commit `.env.local`, `backend/.env`, `node_modules`, `.venv`, `.vercel`, or build output.

The model is approximately 92.3 MiB, close to GitHub's 100 MiB per-file limit. Avoid storing duplicate versions; plan artifact storage if it grows. Pickle files execute code when loaded: use only trusted model artifacts.

## Deployment

This project uses [Vercel Services](https://vercel.com/docs/services), currently in beta, to deploy Vite and FastAPI together. `vercel.json` routes `/api/*` to the Python service (FastAPI mounts that prefix explicitly) and all other requests to the frontend. Preview deployments use their own API automatically.

1. In Vercel, choose **Add New → Project** and import `KshitijChaudhari25/Coral_Reef`.
2. Use the repository root. Keep build overrides unset: the service configuration selects Vite, `npm ci`, `npm run build`, `dist`, and FastAPI `main:app`.
3. Leave `VITE_API_URL` unset (or set `/api`). Never copy the local localhost value into Vercel.
4. Under **Settings → Environment Variables**, optionally add `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` for Production and Preview. These values are public; configure the feedback table and RLS first.
5. Add `OPENROUTER_API_KEY` as a private/sensitive variable only in environments where chat should work. Optionally set `OPENROUTER_MODEL`; set `SITE_URL` to your production URL. Never prefix private keys with `VITE_`.
6. Same-origin API requests do not need cross-origin allowances. Set `CORS_ORIGINS` only for additional frontend origins you intentionally allow.
7. Deploy, then check `/api/health`, prediction, simulation, live data, and any configured optional features. Environment changes require a new deployment to take effect.

The Python service pins Python 3.14 and uses `requirements-lock.txt` constraints. The model must be included in Git. If Vercel reports a Python bundle size error, inspect the actual build logs before changing limits or removing model artifacts. `render.yaml` remains an optional alternative for hosting FastAPI separately; in that arrangement set the frontend's `VITE_API_URL` to the backend's HTTPS URL and configure CORS there.

## Publish from PowerShell

After installing GitHub CLI and signing in (`gh auth login`), run from the project root:

```powershell
git init -b main
git add .
git diff --cached --stat
git diff --cached --name-only
# Confirm only templates, not actual .env files, are staged.
git commit -m "Prepare Coral Reef dashboard for deployment"
gh repo create KshitijChaudhari25/Coral_Reef --public --source=. --remote=origin --push
```

Run repository creation only once. For later changes, use `git add`, `git commit`, and `git push`. The archived `Code_Documentation.pdf` is excluded because it contains outdated source and author information; this README and the maintained source supersede it.

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

## Data and limitations

Predictions and scenario simulations are educational estimates, not validated forecasts. NOAA availability, geolocation accuracy, model training quality, and third-party service terms affect the result. The software license does not grant rights to third-party datasets, fonts, map tiles, or API services.

## Author and license

**Kshitij Chaudhari**

Copyright (c) 2026 Kshitij Chaudhari. Software is released under the [MIT License](LICENSE).
