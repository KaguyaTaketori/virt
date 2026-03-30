from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import (
    streams,
    channels,
    danmaku,
    admin,
    websocket,
    organizations,
    auth,
    user_channels,
)
from app.services.youtube_websub import router as youtube_websub_router
from app.database import engine, Base
from app.scheduler_tasks import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield


app = FastAPI(
    title="VTuber Live Aggregator API",
    description="聚合 YouTube 和 Bilibili 直播流的后端 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(streams.router)
app.include_router(channels.router)
app.include_router(danmaku.router)
app.include_router(admin.router)
app.include_router(websocket.router)
app.include_router(organizations.router)
app.include_router(auth.router)
app.include_router(user_channels.router)
app.include_router(youtube_websub_router)


@app.get("/")
def root():
    return {"message": "VTuber Live Aggregator API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
