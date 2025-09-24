# Emerging Market Swap Curve Fitter

FastAPI web service that emits synthetic emerging market swap curves via Server-Sent Events (SSE). The service currently generates randomised curve marks and fits a polynomial over a dense tenor grid to mimic intraday pricing snapshots.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app
```

The app listens on port 8000 by default. You can also run it with `uvicorn app.main:app --reload` during development.

## Endpoints

- `GET /` – basic service metadata
- `GET /health` – readiness probe returning `{ "status": "ok" }`
- `GET /curves/stream` – SSE stream of curve snapshots. Supports optional `interval` query parameter (seconds between snapshots).

## Consuming the stream

Event data is JSON encoded. A quick way to try the feed is to use `curl`:

```bash
curl -N "http://127.0.0.1:8000/curves/stream?interval=2"
```

Sample event payload:

```json
{
  "timestamp": "2024-05-11T09:00:00.123456+00:00",
  "tenorYears": [0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0],
  "rawRates": [8.32, 8.12, 8.05, 8.11, 8.36, 8.55, 8.87, 9.25, 9.64, 9.85, 10.04],
  "fit": {
    "gridYears": [0.5, 0.75, ...],
    "rates": [8.36, 8.30, ...],
    "polynomialCoefficients": [0.0002, -0.013, 0.25, 0.18, 7.95]
  }
}
```

Adjust the stream interval or integrate the endpoint into a frontend to visualise the evolving curve.

## Continuous delivery

A GitHub Actions workflow at `.github/workflows/docker-publish.yml` builds the Docker image with Buildx and publishes it to GitHub Container Registry (`ghcr.io/<owner>/<repo>`) whenever `main` is updated. Grant the repository's `GITHUB_TOKEN` the `packages: write` permission (enabled by default on public repos) to allow the push to succeed.
