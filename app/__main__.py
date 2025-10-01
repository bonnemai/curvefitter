"""Run the FastAPI app with uvicorn when executed as a module."""
import uvicorn


def main() -> None:
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=False, log_level="info")


if __name__ == "__main__":
    main()
