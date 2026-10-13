import sys
import os
import math
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import httpx
import asyncio
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, FiniteFloat
from typing import Literal

from predict import load_model, predict_risk
from simulate import simulate_scenario

# Host environment takes precedence over the local, ignored file.
load_dotenv(Path(__file__).with_name('.env'))
CORS_ORIGINS = [origin.strip().rstrip('/') for origin in os.getenv(
    'CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173'
).split(',') if origin.strip()]

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Coral Reef Bleaching Predictor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fail at startup with a useful error if any required model artifact is missing.
MODEL_DIR = os.path.join(os.path.dirname(__file__), "model_files")
model, scaler, features = load_model(MODEL_DIR)


# ── NOAA ERDDAP Live Data ─────────────────────────────────────────────────────

# NOAA's former CoastWatch URL now redirects to this PacIOOS dataset.
NOAA_BASE = "https://pae-paha.pacioos.hawaii.edu/erddap/griddap/dhw_5km.csv"

ZONES = {
    "Great Barrier Reef": {"lat": -18.0, "lon": 147.0},
    "Coral Triangle":     {"lat":  0.0,  "lon": 125.0},
    "Caribbean":          {"lat": 15.0,  "lon": -66.0},
    "Red Sea":            {"lat": 21.0,  "lon":  38.0},
    "Indian Ocean":       {"lat": -5.0,  "lon":  73.0},
}

VARIABLES = ["CRW_SST", "CRW_SSTANOMALY", "CRW_DHW", "CRW_BAA"]

# ── In-memory cache ───────────────────────────────────────────────────────────
_live_cache = {
    "data": None,
    "fetched_at": None,
    "ttl_minutes": 60,
}

# ── Per-IP rate limit tracker ─────────────────────────────────────────────────
# { ip_str: [timestamp, timestamp, ...] }
_rate_limit_tracker: dict[str, list] = defaultdict(list)
RATE_LIMIT_MAX = 10       # requests
RATE_LIMIT_WINDOW = 60    # seconds


def _check_rate_limit(ip: str) -> bool:
    """Returns True if IP is within rate limit, False if exceeded."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
    # Remove inactive clients so the tracker cannot grow indefinitely.
    for key in list(_rate_limit_tracker):
        if not _rate_limit_tracker[key] or _rate_limit_tracker[key][-1] <= window_start:
            del _rate_limit_tracker[key]
    if ip not in _rate_limit_tracker and len(_rate_limit_tracker) >= 10000:
        return False
    timestamps = _rate_limit_tracker[ip]
    # Purge old entries outside the window
    _rate_limit_tracker[ip] = [t for t in timestamps if t > window_start]
    if len(_rate_limit_tracker[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit_tracker[ip].append(now)
    return True


async def fetch_zone_variables(client: httpx.AsyncClient, lat: float, lon: float) -> dict:
    """Fetch all four readings in one request; preserve missing data as null."""
    empty = {variable: None for variable in VARIABLES}
    suffix = f"[(last)][({lat:.1f}):1:({lat:.1f})][({lon:.1f}):1:({lon:.1f})]"
    url = NOAA_BASE + '?' + ','.join(variable + suffix for variable in VARIABLES)
    try:
        response = await client.get(url, timeout=12.0)
        response.raise_for_status()
        lines = response.text.strip().splitlines()
        if len(lines) < 3:
            return empty
        row = dict(zip(lines[0].split(','), lines[2].split(',')))
        result = {}
        for variable in VARIABLES:
            try:
                value = float(row[variable])
                result[variable] = value if math.isfinite(value) else None
            except (KeyError, ValueError):
                result[variable] = None
        return result
    except httpx.HTTPError:
        return empty


async def fetch_all_live_data() -> dict:
    # One request per zone prevents the former 20-request fanout.
    async with httpx.AsyncClient(
        timeout=12.0,
        limits=httpx.Limits(max_connections=5),
        follow_redirects=True,
    ) as client:
        results = await asyncio.gather(*(
            fetch_zone_variables(client, coords['lat'], coords['lon'])
            for coords in ZONES.values()
        ))
    zone_raw = dict(zip(ZONES, results))

    # Build response structure
    zones_out = {}
    for zone_name in ZONES:
        raw = zone_raw[zone_name]
        sst         = raw.get("CRW_SST")
        sst_anomaly = raw.get("CRW_SSTANOMALY")
        dhw         = raw.get("CRW_DHW")
        baa_raw     = raw.get("CRW_BAA")

        # BAA is an integer-valued float
        alert_level = int(round(baa_raw)) if baa_raw is not None else None

        alert_labels = {
            0: "No Stress", 1: "Watch", 2: "Warning",
            3: "Alert 1", 4: "Alert 2", 5: "Alert 2+",
        }
        alert_label = alert_labels.get(alert_level, "Unknown") if alert_level is not None else "Unknown"

        # Risk from DHW / BAA
        if dhw is None and baa_raw is None:
            risk, risk_color = "UNKNOWN", "#64748b"
        elif dhw is not None and dhw < 4:
            risk, risk_color = "LOW", "#2ecc71"
        elif dhw is not None and 4 <= dhw <= 8:
            risk, risk_color = "MODERATE", "#f39c12"
        elif (dhw is not None and dhw > 8) or (alert_level is not None and alert_level >= 3):
            risk, risk_color = "HIGH", "#e74c3c"
        else:
            risk, risk_color = "UNKNOWN", "#64748b"

        # Data quality
        loaded = sum(1 for v in [sst, sst_anomaly, dhw, baa_raw] if v is not None)
        if loaded == 4:
            data_quality = "complete"
        elif loaded == 0:
            data_quality = "unavailable"
        else:
            data_quality = "partial"

        zones_out[zone_name] = {
            "sst":         round(sst, 2)         if sst is not None else None,
            "sst_anomaly": round(sst_anomaly, 2) if sst_anomaly is not None else None,
            "dhw":         round(dhw, 2)         if dhw is not None else None,
            "alert_level": alert_level,
            "alert_label": alert_label,
            "risk":        risk,
            "risk_color":  risk_color,
            "data_quality": data_quality,
        }

    return zones_out


# ── Schemas ───────────────────────────────────────────────────────────────────

class PredictInput(BaseModel):
    Temperature_Mean_Celsius: FiniteFloat
    SSTA:                     FiniteFloat
    SSTA_DHW:                 FiniteFloat
    TSA_DHW:                  FiniteFloat
    Turbidity:                FiniteFloat
    Cyclone_Frequency:        FiniteFloat
    Windspeed:                FiniteFloat
    Depth_m:                  FiniteFloat
    SSTA_FrequencyMax:        FiniteFloat
    TSA_Mean:                 FiniteFloat   # user gives positive; predict.py auto-negates
    ClimSST:                  FiniteFloat   # user gives Celsius; predict.py auto +273.15
    TSA_Frequency:            FiniteFloat


class BaselineInputs(BaseModel):
    Temperature_Mean_Celsius: FiniteFloat
    SSTA:                     FiniteFloat
    SSTA_DHW:                 FiniteFloat
    TSA_DHW:                  FiniteFloat
    Turbidity:                FiniteFloat
    Cyclone_Frequency:        FiniteFloat
    Windspeed:                FiniteFloat
    Depth_m:                  FiniteFloat
    SSTA_FrequencyMax:        FiniteFloat
    TSA_Mean:                 FiniteFloat
    ClimSST:                  FiniteFloat
    SSTA_Mean:                FiniteFloat = 0.0
    TSA_Frequency:            FiniteFloat


class SimulateInput(BaseModel):
    baseline_inputs: BaselineInputs
    scenario:        str = "status_quo"   # optimistic | status_quo | worst_case
    years:           int = Field(default=10, ge=1, le=100)


class ChatMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=2000)


class ChatInput(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


CHAT_SYSTEM_PROMPT = (
    'You are the Reef Assistant for the Coral Reef Bleaching Prediction Dashboard '
    'created by Kshitij Chaudhari. Answer questions about coral bleaching, sea '
    'surface temperature, thermal anomalies, degree heating weeks, the five reef '
    'zones, conservation, climate change, and the dashboard. Politely decline '
    'unrelated topics. Explain that model predictions are educational estimates.'
)


@app.post('/chat')
async def chat(body: ChatInput, request: Request):
    api_key = os.getenv('OPENROUTER_API_KEY', '').strip()
    if not api_key:
        raise HTTPException(status_code=503, detail='The Reef Assistant is not configured yet.')
    if body.messages[-1].role != 'user':
        raise HTTPException(status_code=422, detail='The last message must be from the user.')
    client_ip = request.client.host if request.client else 'unknown'
    if not _check_rate_limit(f'chat:{client_ip}'):
        raise HTTPException(status_code=429, detail='Please wait a minute before sending another message.')
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'HTTP-Referer': os.getenv('SITE_URL', 'http://localhost:5173'),
                    'X-Title': 'Coral Reef Dashboard',
                },
                json={
                    'model': os.getenv('OPENROUTER_MODEL') or 'openrouter/auto',
                    'messages': [{'role': 'system', 'content': CHAT_SYSTEM_PROMPT}]
                        + [message.model_dump() for message in body.messages],
                    'max_tokens': 400,
                    'temperature': 0.7,
                },
            )
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            if not isinstance(content, str) or not content.strip():
                raise ValueError('Empty provider response')
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail='The Reef Assistant timed out. Please try again.') from None
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        # Never forward provider responses or credentials to the browser.
        raise HTTPException(status_code=502, detail='The Reef Assistant is temporarily unavailable.') from None
    return {'content': content}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "features": features}


@app.get("/live-data")
async def live_data(request: Request):
    # ── Rate limiting ─────────────────────────────────────────────────────────
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return JSONResponse(
            status_code=429,
            content={
                "status": "rate_limited",
                "message": "Too many requests — data refreshes every 60 minutes",
            },
        )

    now = datetime.now(timezone.utc)

    # ── Serve from cache if still fresh ──────────────────────────────────────
    if _live_cache["data"] is not None and _live_cache["fetched_at"] is not None:
        age_minutes = (now - _live_cache["fetched_at"]).total_seconds() / 60
        if age_minutes < _live_cache["ttl_minutes"]:
            zones = _live_cache["data"]
            zones_failed = sum(
                1 for z in zones.values() if z["data_quality"] == "unavailable"
            )
            return {
                "status": "cached",
                "fetched_at": _live_cache["fetched_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "cache_age_minutes": round(age_minutes, 1),
                "source": "NOAA Coral Reef Watch ERDDAP",
                "source_url": "https://coralreefwatch.noaa.gov",
                "zones": zones,
                "zones_loaded": len(ZONES) - zones_failed,
                "zones_failed": zones_failed,
            }

    # ── Fetch fresh data from NOAA ────────────────────────────────────────────
    try:
        zones = await fetch_all_live_data()
    except Exception:
        # If NOAA is completely unreachable, return 503
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "message": "Live satellite feed temporarily unavailable",
                "fallback": "historical",
            },
        )

    # Check if everything is unavailable (total failure)
    all_unavailable = all(
        z["data_quality"] == "unavailable" for z in zones.values()
    )
    if all_unavailable:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "message": "Live satellite feed temporarily unavailable",
                "fallback": "historical",
            },
        )

    # ── Update cache ──────────────────────────────────────────────────────────
    _live_cache["data"] = zones
    _live_cache["fetched_at"] = now

    zones_failed = sum(
        1 for z in zones.values() if z["data_quality"] == "unavailable"
    )

    return {
        "status": "live",
        "fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cache_age_minutes": 0,
        "source": "NOAA Coral Reef Watch ERDDAP",
        "source_url": "https://coralreefwatch.noaa.gov",
        "zones": zones,
        "zones_loaded": len(ZONES) - zones_failed,
        "zones_failed": zones_failed,
    }


@app.post("/predict")
def predict(body: PredictInput):
    # Build the 13-key input dict; SSTA_Mean is always hardcoded to 0.0
    input_data = {
        "Temperature_Mean_Celsius": body.Temperature_Mean_Celsius,
        "SSTA":                     body.SSTA,
        "SSTA_DHW":                 body.SSTA_DHW,
        "TSA_DHW":                  body.TSA_DHW,
        "Turbidity":                body.Turbidity,
        "Cyclone_Frequency":        body.Cyclone_Frequency,
        "Windspeed":                body.Windspeed,
        "Depth_m":                  body.Depth_m,
        "SSTA_FrequencyMax":        body.SSTA_FrequencyMax,
        "TSA_Mean":                 body.TSA_Mean,
        "ClimSST":                  body.ClimSST,
        "SSTA_Mean":                0.0,          # hardcoded — never exposed as slider
        "TSA_Frequency":            body.TSA_Frequency,
    }

    result = predict_risk(model, scaler, features, input_data)

    if result is None:
        raise HTTPException(status_code=422, detail="Input validation failed — check feature values.")

    return result


@app.post("/simulate")
def simulate(body: SimulateInput):
    valid_scenarios = {"optimistic", "status_quo", "worst_case"}
    if body.scenario not in valid_scenarios:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario '{body.scenario}'. Valid: {sorted(valid_scenarios)}"
        )

    # Build the baseline dict (keep SSTA_Mean = 0.0 to match model training)
    baseline = body.baseline_inputs.model_dump()
    baseline["SSTA_Mean"] = 0.0

    df = simulate_scenario(
        baseline_inputs=baseline,
        scenario=body.scenario,
        years=body.years,
    )

    return df.to_dict(orient="records")
