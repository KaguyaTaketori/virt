# VTuber Live - 直播聚合平台

VTuber Live 是一个支持多平台直播源统一管理和多视图观看的直播聚合平台。

## 项目架构

```
virt/
├── backend/           # FastAPI 后端服务
│   ├── app/
│   │   ├── core/      # 核心配置
│   │   ├── database/  # 数据库模型
│   │   ├── integrations/  # 第三方集成
│   │   ├── models/    # 数据模型
│   │   ├── repositories/  # 数据仓库
│   │   ├── routers/   # API 路由
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # 业务逻辑
│   │   ├── utils/     # 工具函数
│   │   └── worker/    # 后台任务
│   └── migrations/    # 数据库迁移
└── frontend/          # Vue 3 前端
    └── src/
        ├── api/       # API 接口
        ├── components/ # 公共组件
        ├── composables/ # 组合式函数
        ├── views/     # 页面视图
        └── stores/    # Pinia 状态
```

## 技术栈

### 后端

- **框架**: FastAPI
- **数据库**: SQLAlchemy + SQLite
- **任务调度**: APScheduler
- **认证**: JWT (python-jose)
- **直播源处理**: yt-dlp, yt-chat-downloader
- **平台集成**: bilibili-api-python
- **缓存**: Redis
- **日志**: Loguru
- **迁移**: Alembic

### 前端

- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI 组件**: Naive UI
- **状态管理**: Pinia
- **路由**: Vue Router
- **数据请求**: Axios + Vue Query
- **样式**: Tailwind CSS
- **布局**: GridStack

## 快速开始

### 后端

```bash
cd backend

# 使用 uv 管理依赖 (推荐)
uv sync

# 或手动创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

pip install -e .

# 运行服务
uvicorn app.main:app --reload --port 8000
```

**环境要求**: Python >= 3.11

### 前端

```bash
cd frontend

# 安装依赖
bun install

# 开发模式
bun run dev

# 构建
bun run build
```

## 环境配置

### 后端 (.env)

```env
DATABASE_URL=sqlite:///./streams.db
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
BILIBILI_COOKIE=your-cookie
```

### 前端 (.env)

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 主要功能

- 多视图观看 - 网格布局同时观看多个直播源
- 频道管理 - 管理 B 站等平台的直播频道
- 直播流聚合 - 统一管理多平台直播源
- 用户认证 - 支持登录和权限管理
- 实时弹幕 - 集成各平台弹幕系统

## API 端点

| 端点 | 描述 |
|------|------|
| `/api/streams` | 直播流管理 |
| `/api/channels` | 频道管理 |
| `/api/users` | 用户管理 |
| `/api/auth` | 认证接口 |
| `/api/bilibili` | B站集成 |

## 页面路由 (前端)

| 路径 | 页面 |
|------|------|
| `/` | 首页 |
| `/channels` | 频道列表 |
| `/multiview` | 多视图观看 |
| `/settings` | 设置页 |
| `/login` | 登录页 |
| `/admin/*` | 管理后台 |

## 开发命令

```bash
# 后端类型检查
cd backend && ruff check .

# 前端类型检查
cd frontend && bun run type-check

# 数据库迁移
cd backend && alembic upgrade head
```