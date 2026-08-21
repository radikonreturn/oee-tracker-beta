from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models import Base
from routers import (
    downtime_events,
    downtime_reasons,
    machines,
    oee,
    production_runs,
    shifts,
    views,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="OEETracker API",
    description="Single-tenant OEE and changeover-time tracking API for manufacturing workshops.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTML Views Router (no prefix)
app.include_router(views.router)

# JSON API Routers
app.include_router(machines.router, prefix="/api")
app.include_router(shifts.router, prefix="/api")
app.include_router(downtime_reasons.router, prefix="/api")
app.include_router(downtime_events.router, prefix="/api")
app.include_router(production_runs.router, prefix="/api")
app.include_router(oee.router, prefix="/api")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": "OEETracker API", "version": "1.0.0"}
