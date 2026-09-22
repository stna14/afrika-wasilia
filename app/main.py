from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.redis_client import close_redis, get_redis

import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.APP_NAME} [{settings.ENV}]")

    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    print("  DB connection OK")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  Tables ensured")

    r = get_redis()
    await r.ping()
    print("  Redis connection OK")

    yield

    await engine.dispose()
    await close_redis()
    print("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["root"])
async def root():
    return {"service": settings.APP_NAME, "env": settings.ENV, "status": "ok"}


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy", "env": settings.ENV}


@app.get("/health/db", tags=["health"])
async def health_db():
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
        return {"status": "healthy", "service": "mysql"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "service": "mysql", "error": str(e)},
        )


@app.get("/health/redis", tags=["health"])
async def health_redis():
    try:
        r = get_redis()
        await r.ping()
        return {"status": "healthy", "service": "redis"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "service": "redis", "error": str(e)},
        )