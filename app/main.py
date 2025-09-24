"""FastAPI application that streams random emerging market swap curves via SSE."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, List

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI(
    title="Emerging Market Swap Curve Fitter",
    description=(
        "Streams synthetic emerging market swap curves and their polynomial fits "
        "as server-sent events."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenors that roughly align with LCH cleared BRL swap grid, expressed in years.
TENOR_YEARS = np.array([0.5, 1, 2, 3, 4, 5, 7, 10, 15, 20, 30], dtype=float)
# Dense grid for reporting the fitted curve back to the client.
FITTED_GRID = np.linspace(0.5, 30.0, num=120)


def _base_em_curve(tenors: np.ndarray) -> np.ndarray:
    """Create a stylised emerging-market swap curve profile."""
    short_end = 8.0 - 0.8 * np.exp(-tenors)
    term_premium = 1.4 * (1.0 - np.exp(-tenors / 7.0))
    cyclical_component = 0.25 * np.sin(tenors / 1.5)
    liquidity_drag = 0.35 * np.exp(-(tenors - 12.0) ** 2 / 30.0)
    return short_end + term_premium + cyclical_component + liquidity_drag


def _sample_raw_rates(tenors: np.ndarray) -> np.ndarray:
    """Perturb the base curve with noise to emulate daily marks."""
    base_curve = _base_em_curve(tenors)
    shock_scale = np.linspace(0.15, 0.6, num=tenors.size)
    shocks = np.random.normal(loc=0.0, scale=shock_scale)
    return np.maximum(base_curve + shocks, 1.5)


def _fit_curve(
    tenors: np.ndarray, rates: np.ndarray, grid: np.ndarray, degree: int = 4
) -> Dict[str, List[float]]:
    """Fit a polynomial to the raw rates and evaluate on the target grid."""
    rate_variance = float(np.var(rates))
    if rate_variance == 0:
        raise HTTPException(status_code=400, detail="Cannot fit curve without variance")

    coefficients = np.polyfit(tenors, rates, deg=degree)
    fitted_rates = np.polyval(coefficients, grid)
    return {
        "gridYears": grid.tolist(),
        "rates": fitted_rates.tolist(),
        "polynomialCoefficients": coefficients.tolist(),
    }


def _build_curve_snapshot() -> Dict[str, object]:
    """Create a JSON-serialisable snapshot containing raw and fitted curves."""
    raw_rates = _sample_raw_rates(TENOR_YEARS)
    fitted = _fit_curve(TENOR_YEARS, raw_rates, FITTED_GRID)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenorYears": TENOR_YEARS.tolist(),
        "rawRates": raw_rates.tolist(),
        "fit": fitted,
    }


async def _curve_event_stream(interval: float) -> AsyncIterator[str]:
    """Yield swap curve snapshots as SSE data frames."""
    while True:
        payload = json.dumps(_build_curve_snapshot())
        yield f"data: {payload}\n\n"
        await asyncio.sleep(interval)


@app.get("/curves/stream")
async def stream_swap_curves(interval: float = 1.0) -> StreamingResponse:
    """Stream synthetic emerging market swap curves via SSE."""
    if interval <= 0:
        raise HTTPException(status_code=400, detail="interval must be positive")
    return StreamingResponse(
        _curve_event_stream(interval), media_type="text/event-stream"
    )


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Simple readiness probe."""
    return {"status": "ok"}


@app.get("/")
async def root() -> Dict[str, object]:
    """Return service metadata and helpful links."""
    return {
        "service": app.title,
        "description": app.description,
        "streamEndpoint": "/curves/stream",
        "healthEndpoint": "/health",
        "defaultIntervalSeconds": 1.0,
    }
