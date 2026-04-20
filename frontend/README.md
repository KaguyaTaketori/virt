# VTuber Live - 直播聚合平台

VTuber Live 是一个直播聚合平台，支持多平台直播源的统一管理和多视图观看。

## 技术栈

- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI 组件库**: Naive UI
- **状态管理**: Pinia
- **路由**: Vue Router
- **数据请求**: Axios + Vue Query
- **样式**: Tailwind CSS
- **图标**: Lucide Vue Next
- **布局**: GridStack

## 环境要求

- Node.js >= 18
- Bun (推荐) 或 npm

## 快速开始

### 安装依赖

```bash
bun install
```

### 开发模式

```bash
bun run dev
```

### 类型检查

```bash
bun run type-check
```

### 构建生产版本

```bash
bun run build
```

### 预览生产版本

```bash
bun run preview
```

## 项目结构

```
src/
├── api/          # API 接口定义
├── components/   # 公共组件
├── composables/  # 组合式函数
├── config/       # 配置文件
├── constants/    # 常量定义
├── layouts/      # 布局组件
├── queries/      # Vue Query 定义
├── router/       # 路由配置
├── stores/       # Pinia 状态管理
├── types/        # TypeScript 类型定义
├── utils/        # 工具函数
├── views/        # 页面视图
├── App.vue       # 根组件
├── main.ts       # 入口文件
└── style.css     # 全局样式
```

## 主要功能

- **多视图观看**: 支持网格布局同时观看多个直播源
- **频道管理**: 管理 B 站等平台的直播频道
- **直播流聚合**: 统一管理多平台直播源
- **用户管理**: 支持用户认证和权限管理
- **设置管理**: 自定义应用配置

## 页面路由

| 路径 | 页面 | 描述 |
|------|------|------|
| `/` | Home | 首页 |
| `/channels` | Channels | 频道列表 |
| `/multiview` | MultiView | 多视图观看 |
| `/settings` | Settings | 设置页 |
| `/login` | Login | 登录页 |
| `/bilibili/callback` | BilibiliLogin | B站登录回调 |
| `/admin/*` | Admin* | 管理后台页面 |

## 环境变量

创建 `.env` 文件配置 API 地址：

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 依赖管理

本项目使用 [Bun](https://bun.sh/) 作为包管理器。

```bash
# 添加依赖
bun add <package>

# 添加开发依赖
bun add -d <package>

# 移除依赖
bun remove <package>

# 更新依赖
bun update
```
