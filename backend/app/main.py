"""FastAPI application entry point for NinerLife v2."""

from fastapi import FastAPI

app = FastAPI(
    title="NinerLife API",
    description="Backend API foundation for the NinerLife student planning application.",
    version="0.1.0",
)


@app.get("/")
def read_root() -> dict[str, str]:
    """Return a simple welcome response for the API."""
    return {
        "message": "Welcome to the NinerLife API",
        "version": app.version,
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    """Confirm that the API is available."""
    return {
        "status": "ok",
        "app": "NinerLife API",
    }
