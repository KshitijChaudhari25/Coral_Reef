# Coral Reef

### Explore coral bleaching. Understand environmental risk.

An interactive dashboard for exploring historical coral reef surveys, estimating bleaching risk, and comparing climate scenarios. Built by **Kshitij Chaudhari** with React and FastAPI.

**[Open the live dashboard](https://coral-reef-lake.vercel.app)** · [API documentation](https://coral-reef-lake.vercel.app/api/docs) · [Setup & configuration](docs/CONFIGURATION.md)

## What you can do

- **Explore reef data:** browse historical trends, country comparisons, and an interactive map of survey sites.
- **Estimate bleaching risk:** adjust environmental conditions and view a Random Forest prediction with class probabilities.
- **Compare scenarios:** visualize ten-year projections under optimistic, status quo, and worst-case assumptions.
- **Check ocean conditions:** view satellite readings when the NOAA feed is available, with a historical-data fallback during outages.
- **Ask questions and send feedback:** optional OpenRouter chat and Supabase feedback integrations.

## Built with

| Frontend | Backend | Deployment |
| --- | --- | --- |
| React 18, Vite 8, Tailwind CSS 4 | Python 3.14, FastAPI | Vercel Services |
| Recharts, Leaflet | scikit-learn Random Forest | Automatic deploys from GitHub `main` |

## Repository layout

```text
Coral_Reef/
├── frontend/             React app, browser assets, and frontend configuration
│   ├── src/              Components, hooks, and utilities
│   ├── public/data/      Historical survey dataset
│   └── .env.example      Public frontend settings
├── backend/              FastAPI endpoints, inference, simulation, and tests
│   ├── model_files/      Trained model, scaler, and feature list
│   └── .env.example      Private backend settings
├── docs/                 Configuration, deployment guide, audit, and images
├── scripts/              Standalone diagnostic tools
├── deployment/           Optional alternative hosting configuration
├── vercel.json           Frontend/API service routing
└── LICENSE               MIT license
```

## Run locally

You need **Node.js 24**, **Python 3.14**, and Git. Run these commands in PowerShell:

```powershell
git clone https://github.com/KshitijChaudhari25/Coral_Reef.git
cd Coral_Reef
npm --prefix frontend ci
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item frontend/.env.example frontend/.env.local
Copy-Item backend/.env.example backend/.env
```

Skip the copy commands if you already have local environment files.

**Terminal 1 — start the API:**

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — start the dashboard:**

```powershell
npm --prefix frontend run dev
```

Open **[localhost:5173](http://localhost:5173)**. Local API docs are at [localhost:8000/docs](http://localhost:8000/docs).

Historical charts, predictions, and simulations work without API keys. To enable chat or feedback, follow the [configuration guide](docs/CONFIGURATION.md). Never commit actual environment files or put a private key in a `VITE_*` variable.

## Build and test

From the repository root:

```powershell
npm --prefix frontend run build
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m unittest discover -s backend -p "test_*.py" -v
```

The backend tests cover model inference, simulation, validation, API routing, and mocked provider responses. Keep scikit-learn at the pinned version used by the saved model.

## Deployment

The frontend and API deploy together on Vercel. Changes pushed to `main` trigger a production build. See the [deployment guide](docs/DEPLOYMENT.md) for routing, environment variables, and troubleshooting.

## Limitations

Predictions and simulations are educational estimates, not validated forecasts. Satellite data depends on upstream availability. Chat and feedback require separately configured provider accounts. Third-party data and services retain their own terms.

## Author & license

Created by **Kshitij Chaudhari**. Released under the [MIT License](LICENSE).
