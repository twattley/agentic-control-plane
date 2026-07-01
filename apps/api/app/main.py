from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import close_pool, get_pool
from app.features.repos.controller import router as repos_router
from app.features.runs.controller import router as runs_router
from app.services.runs_service import LeaseConflict, RunNotFound
from app.services.state_machine import IllegalTransition


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="agentic-control-plane API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5400"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(repos_router)
app.include_router(runs_router)


@app.exception_handler(RunNotFound)
async def _run_not_found(_: Request, exc: RunNotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(IllegalTransition)
async def _illegal_transition(_: Request, exc: IllegalTransition) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(LeaseConflict)
async def _lease_conflict(_: Request, exc: LeaseConflict) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
