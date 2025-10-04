"""FastAPI application that streams random emerging market swap curves via SSE."""
from __future__ import annotations

import asyncio
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from mangum import Mangum

_TEMPLATE_ROOT = Path(__file__).resolve().parent / "templates"
_INDEX_TEMPLATE = (_TEMPLATE_ROOT / "index.html").read_text(encoding="utf-8")
allow_origins = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()]
app = FastAPI(
    title="Emerging Market Swap Curve Fitter",
    description=(
        "Streams synthetic emerging market swap curves and their polynomial fits "
        "as server-sent events."
    ),
    version="0.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],   
)
handler = Mangum(app)

# Tenors that roughly align with LCH cleared BRL swap grid, expressed in years.
TENOR_YEARS = np.array([0.5, 1, 2, 3, 4, 5, 7, 10, 15, 20, 30], dtype=float)
# Dense grid for reporting the fitted curve back to the client.
FITTED_GRID = np.linspace(0.5, 30.0, num=120)
MIN_CURVE_RATE = 1.5
MAX_MUTATED_POINTS = 2
MAX_MUTATION_FRACTION = 0.20

try:
    _MUTATION_SEED = int(os.getenv("CURVE_FITTER_MUTATION_SEED", "275352"))
except ValueError:
    _MUTATION_SEED = 275352

_mutation_rng = np.random.default_rng(_MUTATION_SEED)
_curve_state_lock = threading.Lock()
_base_curve: np.ndarray | None = None
_current_raw_rates: np.ndarray | None = None


def _base_em_curve(tenors: np.ndarray) -> np.ndarray:
    """Create a stylised emerging-market swap curve profile."""
    short_end = 8.0 - 0.8 * np.exp(-tenors)
    term_premium = 1.4 * (1.0 - np.exp(-tenors / 7.0))
    cyclical_component = 0.25 * np.sin(tenors / 1.5)
    liquidity_drag = 0.35 * np.exp(-(tenors - 12.0) ** 2 / 30.0)
    return short_end + term_premium + cyclical_component + liquidity_drag


def _sample_raw_rates(tenors: np.ndarray) -> np.ndarray:
    """Mutate up to two points of the curve, capping changes at 20%."""
    global _base_curve, _current_raw_rates

    with _curve_state_lock:
        if _base_curve is None or _current_raw_rates is None:
            _base_curve = _base_em_curve(tenors)
            _current_raw_rates = _base_curve.copy()

        mutation_count = int(
            _mutation_rng.integers(1, MAX_MUTATED_POINTS + 1)
        )
        indices = _mutation_rng.choice(
            tenors.size, size=mutation_count, replace=False
        )

        for idx in np.atleast_1d(indices):
            base_rate = float(_base_curve[idx])
            current_rate = float(_current_raw_rates[idx])
            delta = float(
                _mutation_rng.uniform(-MAX_MUTATION_FRACTION, MAX_MUTATION_FRACTION)
            )
            proposed = current_rate * (1.0 + delta)
            lower_bound = max(base_rate * (1.0 - MAX_MUTATION_FRACTION), MIN_CURVE_RATE)
            upper_bound = base_rate * (1.0 + MAX_MUTATION_FRACTION)
            _current_raw_rates[idx] = float(
                np.clip(proposed, lower_bound, upper_bound)
            )

        return _current_raw_rates.copy()


def _fit_curve(
    tenors: np.ndarray, rates: np.ndarray, grid: np.ndarray, degree: int = 4
) -> dict[str, list[float]]:
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


def _build_curve_snapshot() -> dict[str, object]:
    """Create a JSON-serialisable snapshot containing raw and fitted curves."""
    raw_rates = _sample_raw_rates(TENOR_YEARS)
    fitted = _fit_curve(TENOR_YEARS, raw_rates, FITTED_GRID)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenorYears": TENOR_YEARS.tolist(),
        "rawRates": raw_rates.tolist(),
        "fit": fitted,
    }


async def sse_gen(interval: float) -> AsyncIterator[str]:
    """Yield swap curve snapshots as SSE frames."""
    while True:
        payload = json.dumps(_build_curve_snapshot())
        yield f"data: {payload}\n\n"
        await asyncio.sleep(interval)


@app.get("/curves/stream")
async def stream_swap_curves(interval: float = 1.0) -> StreamingResponse:
    """Stream synthetic emerging market swap curves via SSE."""
    if interval <= 0:
        raise HTTPException(status_code=400, detail="interval must be positive")
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        sse_gen(interval),
        media_type="text/event-stream",
        headers=headers,
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple readiness probe."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """Render the landing page from a static HTML template."""
    html = _INDEX_TEMPLATE.replace("{{version}}", app.version)
    return HTMLResponse(content=html)
