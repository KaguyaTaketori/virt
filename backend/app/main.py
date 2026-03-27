from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import streams, channels, danmaku, admin
from app.database import engine, Base
from app.scheduler_tasks import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：创建数据库表
    Base.metadata.create_all(bind=engine)
    # 启动定时任务
    start_scheduler()
    yield
    # 关闭时：清理资源


app = FastAPI(
    title="VTuber Live Aggregator API",
    description="聚合 YouTube 和 Bilibili 直播流的后端 API",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置 CORS 允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(streams.router)
app.include_router(channels.router)
app.include_router(danmaku.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"message": "VTuber Live Aggregator API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
