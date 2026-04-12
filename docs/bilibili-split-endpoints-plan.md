# B站端点拆分计划

## 目标
按 tab 类型请求对应的数据，避免不必要的请求。

## 当前问题
- `activeTab = useRouteQuery<TabType>('tab', 'videos')` 可以切换 tab
- 但点击 tab 后不会获取对应数据，因为只监听 `channelId`
- 后端 `/api/channels/{id}/bilibili` 一次性返回所有数据

## 新增端点设计

| 端点 | 用途 | 参数 |
|------|------|------|
| `GET /api/channels/{id}/bilibili/info` | 主页 tab | 无 |
| `GET /api/channels/{id}/bilibili/videos` | 投稿 tab | `page`, `page_size` |
| `GET /api/channels/{id}/bilibili/dynamics` | 动态 tab | `offset`, `limit` |

## 实施步骤

### 后端

1. 修改 `backend/app/routers/channels/bilibili.py`
   - 保留原 `/bilibili` 端点（向后兼容）
   - 新增 `/bilibili/info` 端点
   - 新增 `/bilibili/videos` 端点
   - 新增 `/bilibili/dynamics` 端点

2. 修改 `backend/app/services/bilibili_channel_service.py`（或直接在路由中调用 client）

### 前端

1. 修改 `frontend/src/api/index.ts` - 新增3个 API 方法
2. 修改 `frontend/src/composables/useBilibiliData.ts` - 重构为按类型获取
3. 修改 `frontend/src/views/ChannelDetail.vue` - 添加 activeTab 监听逻辑

## 文件变更清单

| 文件 | 操作 |
|------|------|
| `backend/app/routers/channels/bilibili.py` | ✅ 新增3个端点 |
| `backend/app/services/bilibili_channel_service.py` | ✅ 新增3个 dataclass 和函数 |
| `frontend/src/api/index.ts` | ✅ 新增3个 API 方法 |
| `frontend/src/types/index.ts` | ✅ 新增类型定义 |
| `frontend/src/composables/useBilibiliData.ts` | ✅ 重构为按类型获取 |
| `frontend/src/views/ChannelDetail.vue` | ✅ 添加 activeTab 监听逻辑 |

## 完成状态

✅ 后端 3 个新端点已创建:
- `GET /{channel_id}/bilibili/info` - 主页 tab
- `GET /{channel_id}/bilibili/videos` - 投稿 tab  
- `GET /{channel_id}/bilibili/dynamics` - 动态 tab

✅ 前端已修改实现按 tab 获取数据