from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.connection_manager import manager
from app.services.danmaku_poller import poller

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/danmaku/{video_id}")
async def danmaku_websocket(websocket: WebSocket, video_id: str):
    """WebSocket实时弹幕推送"""
    await manager.connect(video_id, websocket)

    # 启动轮询任务
    poller.start_polling(video_id)

    try:
        # 保持连接，等待接收消息（或可以用于接收客户端命令）
        while True:
            data = await websocket.receive_text()
            # 可以扩展：接收客户端命令，如获取历史弹幕等
    except WebSocketDisconnect:
        manager.disconnect(video_id, websocket)

        # 检查是否还有其他连接，没有则停止轮询
        if (
            video_id not in manager.active_connections
            or not manager.active_connections[video_id]
        ):
            poller.stop_polling(video_id)
