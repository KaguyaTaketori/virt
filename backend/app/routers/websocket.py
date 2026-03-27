from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.connection_manager import manager
from app.services.danmaku_poller import poller

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/danmaku/{video_id}")
async def danmaku_websocket(websocket: WebSocket, video_id: str):
    """WebSocket实时弹幕推送"""
    await manager.connect(video_id, websocket)

    poller.start_polling(video_id)

    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(video_id, websocket)

        if (
            video_id not in manager.active_connections
            or not manager.active_connections[video_id]
        ):
            poller.stop_polling(video_id)
