from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup hooks (DB pool, Redis pool) will go here in Stage 2
    print(f"Starting {settings.APP_NAME} [{settings.ENV}]")
    yield
    # Shutdown hooks
    print("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.get("/", tags=["root"])
async def root():
    return {"service": settings.APP_NAME, "env": settings.ENV, "status": "ok"}


@app.get("/health", tags=["health"])
async def health():
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "env": settings.ENV},
    )
