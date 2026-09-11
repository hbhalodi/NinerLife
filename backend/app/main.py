"""FastAPI application entry point for NinerLife v2."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI


from .database import create_database_tables
from .routes import assignments_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Create missing database tables when the API starts."""
    create_database_tables()
    yield


app = FastAPI(
    title="NinerLife API",
    description="Backend API foundation for the NinerLife student planning application.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(assignments_router)


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
