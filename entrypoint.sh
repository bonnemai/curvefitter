#!/bin/sh
set -e

normalize_bool() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes) return 0 ;;
    *) return 1 ;;
  esac
}

if [ -z "${AWS_LAMBDA_RUNTIME_API}" ]; then
  if [ -z "${CURVE_FITTER_LOCAL_SERVER}" ] || normalize_bool "${CURVE_FITTER_LOCAL_SERVER}"; then
    echo "[entrypoint] Starting local FastAPI server via uvicorn"
    exec python -m app.__main__ "$@"
  fi
  echo "[entrypoint] AWS_LAMBDA_RUNTIME_API not set; run with CURVE_FITTER_LOCAL_SERVER=true to launch local server"
  exit 1
fi

if normalize_bool "${CURVE_FITTER_LOCAL_SERVER:-false}"; then
  echo "[entrypoint] CURVE_FITTER_LOCAL_SERVER enabled; starting uvicorn"
  exec python -m app.__main__ "$@"
fi

echo "[entrypoint] Delegating to Lambda bootstrap"
exec /lambda-entrypoint.sh "$@"
