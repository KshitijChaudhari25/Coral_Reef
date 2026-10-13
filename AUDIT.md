# Local setup and audit — 14 October 2026

## Verified

- Frontend production build passes with Vite 8.3.4 and Tailwind 4.3.3.
- npm dependency audit: zero known vulnerabilities after updating the lockfile.
- Python dependency consistency check passes.
- 13 API regression tests pass, including real model inference, simulation,
  finite input validation, CORS, rate limiting, NOAA parsing, and mocked chat.
- Browser prediction returns Low Risk with 60.97% confidence for default inputs;
  the ten-year Status Quo simulation renders.
- A live NOAA request returns all five zones with complete measurements.
- Missing OpenRouter credentials produce a controlled 503 and a readable UI message.
- Git is initialized on `main`. Local environment files, dependencies, build output,
  logs, and Vercel state are ignored; templates and required model files are included.
- A pattern scan of frontend/backend text source found no OpenRouter secrets,
  GitHub tokens, private keys, or literal JWTs. This is not a guarantee that every
  possible credential format or binary document has been inspected.

## Changes

- Moved OpenRouter calls and its private credential into FastAPI `/chat`.
- Removed the keyed browser geolocation fallback; browser GPS and keyless IP
  geolocation remain available.
- Replaced preconfigured shared service values with safe environment templates.
- Added backend environment loading and exact-origin CORS configuration.
- Pinned scikit-learn to the artifacts' 1.9.0 version and recorded Python constraints.
- Fixed invalid Recharts imports and updated Tailwind integration.
- Corrected the NOAA URL to the redirect destination and combined each zone's
  four variables into one upstream request. Missing readings remain null.
- Made partial satellite readings and disabled feedback explicit in the UI.
- Added setup, validation, and deployment instructions, corrected author credit,
  and generated an MIT license for Kshitij Chaudhari.

- Added same-origin Vercel Services configuration (beta) for Vite and FastAPI.
- Grouped map markers to bound React sibling traversal during development refresh.
- Fixed conflicting status-bar border style properties.

## Configuration still needed

- Chat: put your own `OPENROUTER_API_KEY` into ignored `backend/.env` and restart
  FastAPI. Actual provider authentication and model access have not been tested.
- Feedback: configure your own Supabase URL/public key, `feedback` table, grants,
  and insert-only row-level security. No feedback records were written.
- GitHub: account/repository configuration, initial commit, and push remain.
- Hosting: deploy the backend and frontend, set production environment variables,
  and verify the deployed flows. No deployment was created.

## Remaining observations

- The main JavaScript bundle is about 810 kB (224 kB gzip). Vite emits a size warning;
  this does not fail the build. Lazy loading and chunk splitting can improve it.
- The loaded CSV yields 34,454 dashboard records. Removed the unverified 41,361
  survey/training-count claims from static UI text.
- The old documentation PDF was text-scanned (94 pages, no matches for selected
  credential patterns). It contains stale author/source information and is excluded
  from Git; this is not a comprehensive binary-content security guarantee.
- Recharts 2 is deprecated upstream; migration to Recharts 3 is a separate UI change.
- Starlette warns that its httpx test-client adapter is deprecated. Tests pass.
- The chat rate limiter is in memory and per process. It is not a distributed abuse
  control or authentication layer; configure spending limits and durable controls
  before running a public paid chat service at scale.
- The model is approximately 92.3 MiB. It fits below GitHub's 100 MiB per-file limit
  but future versions may require external artifact storage.
- Live data, map tiles, fonts, and geolocation still depend on external services.

## Run again

See `Readme.md` for exact PowerShell install/start/check commands. Development
servers started during this audit listen only on localhost ports 5173 and 8000.
Their process IDs and logs are in the ignored `.cache` directory.
