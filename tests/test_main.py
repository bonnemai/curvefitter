"""Unit tests for the synthetic curve FastAPI service."""

from __future__ import annotations

import asyncio
import json
from typing import Iterator

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import main


class _DeterministicRng:
    """Deterministic RNG stub to make curve mutations predictable in tests."""

    def __init__(self, indices: Iterator[int], delta: float) -> None:
        self._indices = list(indices)
        self._delta = delta

    def integers(self, low: int, high: int) -> int:  # noqa: D401 - numpy compatible signature
        return len(self._indices)

    def choice(self, a, size=None, replace=False):  # type: ignore[override]
        return np.array(self._indices)

    def uniform(self, low: float, high: float) -> float:  # noqa: D401 - numpy compatible signature
        return self._delta


@pytest.fixture(autouse=True)
def _reset_curve_state() -> Iterator[None]:
    """Ensure global mutation state is reset after each test."""
    original_rng = main._mutation_rng
    main._base_curve = None
    main._current_raw_rates = None
    yield
    main._base_curve = None
    main._current_raw_rates = None
    main._mutation_rng = original_rng


def test_base_em_curve_is_positive_and_monotonic():
    tenors = np.linspace(0.5, 10.0, num=20)
    curve = main._base_em_curve(tenors)
    assert curve.shape == tenors.shape
    assert np.all(curve > 0)
    assert curve[-1] > curve[0]


def test_sample_raw_rates_respects_bounds():
    main._mutation_rng = _DeterministicRng(indices=[0], delta=0.19)
    rates = main._sample_raw_rates(main.TENOR_YEARS)
    baseline = main._base_curve[0]
    mutated = rates[0]
    assert mutated != baseline
    assert mutated <= baseline * (1.0 + main.MAX_MUTATION_FRACTION)
    assert mutated >= max(
        baseline * (1.0 - main.MAX_MUTATION_FRACTION), main.MIN_CURVE_RATE
    )


def test_sample_raw_rates_reuses_existing_state_with_multiple_mutations():
    main._mutation_rng = _DeterministicRng(indices=[0, 1], delta=0.1)
    first = main._sample_raw_rates(main.TENOR_YEARS)
    original_second = first[1]

    main._mutation_rng = _DeterministicRng(indices=[1], delta=-0.2)
    second = main._sample_raw_rates(main.TENOR_YEARS)

    assert not np.array_equal(first, second)
    assert second[1] <= original_second


def test_sample_raw_rates_honors_min_curve_floor(monkeypatch):
    monkeypatch.setattr(main, "MIN_CURVE_RATE", 8.5)
    main._mutation_rng = _DeterministicRng(indices=[0], delta=-0.2)
    rates = main._sample_raw_rates(main.TENOR_YEARS)
    assert rates[0] == pytest.approx(8.5)


def test_fit_curve_returns_expected_polynomial():
    tenors = np.array([1.0, 2.0, 3.0])
    rates = np.array([2.0, 4.0, 6.0])
    grid = np.array([1.0, 2.0, 3.0])
    result = main._fit_curve(tenors, rates, grid, degree=1)
    assert result["gridYears"] == pytest.approx(grid.tolist())
    assert result["rates"] == pytest.approx(rates.tolist())
    assert len(result["polynomialCoefficients"]) == 2


def test_fit_curve_rejects_zero_variance():
    tenors = np.array([1.0, 2.0, 3.0])
    rates = np.array([5.0, 5.0, 5.0])
    grid = np.array([1.0, 2.0, 3.0])
    with pytest.raises(main.HTTPException) as exc:
        main._fit_curve(tenors, rates, grid)
    assert exc.value.status_code == 400


def test_build_curve_snapshot_includes_expected_shapes():
    main._mutation_rng = _DeterministicRng(indices=[0], delta=0.0)
    snapshot = main._build_curve_snapshot()

    assert set(snapshot) == {"timestamp", "tenorYears", "rawRates", "fit"}
    assert snapshot["tenorYears"] == pytest.approx(main.TENOR_YEARS.tolist())
    assert len(snapshot["fit"]["gridYears"]) == main.FITTED_GRID.size
    assert len(snapshot["fit"]["rates"]) == main.FITTED_GRID.size


@pytest.mark.asyncio
async def test_sse_gen_yields_json(monkeypatch):
    payload = {"message": "hello"}
    monkeypatch.setattr(main, "_build_curve_snapshot", lambda: payload)
    stream = main.sse_gen(interval=0)
    data = await asyncio.wait_for(anext(stream), timeout=1)
    assert data.startswith("data: ")
    event = json.loads(data.removeprefix("data: ").strip())
    assert event == payload


def test_stream_endpoint_rejects_non_positive_interval():
    client = TestClient(main.app)
    response = client.get("/baskets/stream", params={"interval": 0})
    assert response.status_code == 400


def test_stream_endpoint_sets_sse_headers(monkeypatch):

    async def _dummy_stream(interval: float):
        yield "data: dummy\\n\\n"

    monkeypatch.setattr(main, "sse_gen", _dummy_stream)
    client = TestClient(main.app)

    with client.stream("GET", "/baskets/stream") as response:
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"
        iterator = response.iter_text()
        assert next(iterator) == "data: dummy\n\n"

@pytest.mark.skip('In progress. ')
def test_stream_endpoint_returns_streaming_response(monkeypatch):

    async def _dummy_stream(interval: float):
        assert np.isclose(interval, 0.1, rtol=1e-09, atol=1e-09)
        yield "data: dummy\\n\\n"

    monkeypatch.setattr(main, "sse_gen", _dummy_stream)
    client = TestClient(main.app)

    with client.stream("GET", "/baskets/stream", params={"interval": 0.1}) as response:
        assert response.status_code == 200
        iterator = response.iter_text()
        assert next(iterator) == "data: dummy\n\n"


def test_health_endpoint_returns_status():
    client = TestClient(main.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint_injects_version():
    client = TestClient(main.app)
    response = client.get("/")
    assert response.status_code == 200
    assert main.app.version in response.text
