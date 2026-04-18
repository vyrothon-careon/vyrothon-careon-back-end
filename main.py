from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import engine, Base
from routers.health import router as health_router
from routers.vitals import router as vitals_router
from routers.auth import router as auth_router
from routers.onboarding import router as onboarding_router
from routers.user_vitals import router as user_vitals_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup event: run create_all to init tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup logic (if any) goes here

app = FastAPI(title="VitalWatch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api")
app.include_router(user_vitals_router, prefix="/api")
