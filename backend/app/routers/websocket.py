# backend/app/routers/websocket.py
import asyncio
import json
from app.loggeruru_config import loggerger
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.connection_manager import manager
from app.services.danmaku_poller import poller

try:
    from app.services.danmaku_youtube import get_chat_from_file

    DANMAKU_YT_AVAILABLE = True
except ImportError:
    DANMAKU_YT_AVAILABLE = False
    get_chat_from_file = None

router = APIRouter(tags=["websocket"])

HEARTBEAT_INTERVAL = 25  # 秒，低于大多数代理的 30s 超时阈值


@router.websocket("/ws/danmaku/{video_id}")
async def danmaku_websocket(websocket: WebSocket, video_id: str):
    """
    实时弹幕推送 WebSocket。
    - 每 25 秒发送心跳 ping，防止代理/CDN 因空闲断连
    - 客户端断连后，如无其他订阅者则停止轮询
    - 客户端可发送 {"type": "time", "currentTime": xxx} 同步视频时间，获取对应弹幕
    """
    await manager.connect(video_id, websocket)
    poller.start_polling(video_id)

    last_sent_times: set = set()

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=HEARTBEAT_INTERVAL,
                )
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif msg.get("type") == "time":
                        current_time = msg.get("currentTime", 0)
                        if DANMAKU_YT_AVAILABLE and get_chat_from_file:
                            messages = get_chat_from_file(video_id)
                            if messages:
                                time_window = 3
                                new_messages = []
                                for m in messages:
                                    ts = m.get("timestamp") or m.get("time")
                                    if ts is None:
                                        continue
                                    try:
                                        msg_time = float(ts)
                                    except (ValueError, TypeError):
                                        continue
                                    if (
                                        msg_time >= current_time
                                        and msg_time < current_time + time_window
                                    ):
                                        if m.get("messageId") not in last_sent_times:
                                            new_messages.append(m)
                                            last_sent_times.add(m.get("messageId"))
                                if new_messages:
                                    await websocket.send_json(
                                        {"type": "danmaku", "data": new_messages}
                                    )
                            else:
                                await websocket.send_json(
                                    {
                                        "type": "danmaku",
                                        "data": [],
                                        "note": "no_recorded",
                                    }
                                )
                except json.JSONDecodeError:
                    if data == "ping":
                        await websocket.send_json({"type": "pong"})

            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("danmaku/{} 异常断连: {}", video_id, e)
    finally:
        manager.disconnect(video_id, websocket)
        active = manager.active_connections.get(video_id, [])
        if not active:
            poller.stop_polling(video_id)
            logger.info("danmaku/{} 无订阅者，停止轮询", video_id)
