# backend/app/routers/websocket.py
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.connection_manager import manager
from app.services.danmaku_poller import poller

router = APIRouter(tags=["websocket"])

HEARTBEAT_INTERVAL = 25  # 秒，低于大多数代理的 30s 超时阈值


@router.websocket("/ws/danmaku/{video_id}")
async def danmaku_websocket(websocket: WebSocket, video_id: str):
    """
    实时弹幕推送 WebSocket。
    - 每 25 秒发送心跳 ping，防止代理/CDN 因空闲断连
    - 客户端断连后，如无其他订阅者则停止轮询
    """
    await manager.connect(video_id, websocket)
    poller.start_polling(video_id)

    try:
        while True:
            try:
                # 等待客户端消息，超时则主动发心跳
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=HEARTBEAT_INTERVAL,
                )
                # 客户端可发 "ping" 让服务端回 "pong"
                if data == "ping":
                    await websocket.send_json({"type": "pong"})

            except asyncio.TimeoutError:
                # 正常心跳周期
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    # 发送失败说明连接已断
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] danmaku/{video_id} 异常断连: {e}")
    finally:
        manager.disconnect(video_id, websocket)
        active = manager.active_connections.get(video_id, [])
        if not active:
            poller.stop_polling(video_id)
            print(f"[WS] danmaku/{video_id} 无订阅者，停止轮询")