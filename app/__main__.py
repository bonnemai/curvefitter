"""Run the FastAPI app locally when the feature flag is enabled."""

import os

import uvicorn


def _env_true(value: str | None) -> bool:
    if value is None:
        return False
    return value.lower() in {"1", "true", "yes"}


def _should_run_local() -> bool:
    if "AWS_LAMBDA_RUNTIME_API" in os.environ:
        return _env_true(os.getenv("CURVE_FITTER_LOCAL_SERVER"))
    # If not running in Lambda, default to local server unless explicitly disabled
    flag = os.getenv("CURVE_FITTER_LOCAL_SERVER")
    if flag is None:
        return True
    return _env_true(flag)


def main() -> None:
    if not _should_run_local():
        raise SystemExit(
            "Running outside AWS Lambda requires CURVE_FITTER_LOCAL_SERVER=true."
        )

    uvicorn.run(
        "app.main:app",
        host=os.getenv("CURVE_FITTER_LOCAL_HOST", "0.0.0.0"),
        port=int(os.getenv("CURVE_FITTER_LOCAL_PORT", "8080")),
        reload=_env_true(os.getenv("CURVE_FITTER_LOCAL_RELOAD")),
        log_level=os.getenv("CURVE_FITTER_LOCAL_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
