"""FastAPI application entry point for NinerLife v2."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os
from typing import Mapping
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from .database import create_database_tables
from .routes import (
    assignments_router,
    courses_router,
    dashboard_router,
    exams_router,
    study_plan_router,
)

LOCAL_DEVELOPMENT_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def get_cors_origins(environ: Mapping[str, str] | None = None) -> list[str]:
    """Return trusted local origins plus an optional configured frontend origin."""
    environment = os.environ if environ is None else environ
    configured_origin = environment.get("FRONTEND_ORIGIN", "").strip().rstrip("/")
    origins = list(LOCAL_DEVELOPMENT_ORIGINS)

    if configured_origin:
        parsed_origin = urlparse(configured_origin)
        if (
            parsed_origin.scheme not in {"http", "https"}
            or not parsed_origin.netloc
            or parsed_origin.path
            or parsed_origin.params
            or parsed_origin.query
            or parsed_origin.fragment
        ):
            raise ValueError(
                "FRONTEND_ORIGIN must be a complete http:// or https:// origin."
            )
        if configured_origin not in origins:
            origins.append(configured_origin)

    return origins


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(assignments_router)
app.include_router(courses_router)
app.include_router(dashboard_router)
app.include_router(exams_router)
app.include_router(study_plan_router)


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
