import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.loguru_config import logger
from app.services.connection_manager import manager
from app.services.danmaku_poller import poller
from app.services.constants import WS_HEARTBEAT_INTERVAL_SECS

try:
    from app.services.danmaku_youtube import get_chat_from_file
    _DANMAKU_YT_AVAILABLE = True
except ImportError:
    get_chat_from_file = None
    _DANMAKU_YT_AVAILABLE = False

router = APIRouter(tags=["websocket"])


# ── 独立协程：心跳 ────────────────────────────────────────────────────────────

async def _heartbeat_task(websocket: WebSocket) -> None:
    """
    每 25 秒向客户端发送 ping，防止代理/CDN 因空闲断连。
    与消息处理协程并发运行，互不阻塞。
    """
    while True:
        await asyncio.sleep(WS_HEARTBEAT_INTERVAL_SECS)
        try:
            await websocket.send_json({"type": "ping"})
        except Exception:
            break


# ── 弹幕派发：录播时间轴对齐 ─────────────────────────────────────────────────

async def _dispatch_timed_danmaku(
    websocket: WebSocket,
    video_id: str,
    current_time: float,
    last_sent: set,
) -> None:
    """根据客户端上报的播放时间，推送该时间窗口内的录播弹幕。"""
    if not _DANMAKU_YT_AVAILABLE or not get_chat_from_file:
        return

    messages = get_chat_from_file(video_id) or []
    window_end = current_time + 3.0
    batch = []

    for m in messages:
        raw_ts = m.get("timestamp") or m.get("time")
        try:
            t = float(raw_ts)
        except (TypeError, ValueError):
            continue

        mid = m.get("messageId")
        if current_time <= t < window_end and mid not in last_sent:
            batch.append(m)
            last_sent.add(mid)

    payload = (
        {"type": "danmaku", "data": batch}
        if batch
        else {"type": "danmaku", "data": [], "note": "no_recorded"}
    )
    await websocket.send_json(payload)


# ── 消息处理：单条客户端消息 ─────────────────────────────────────────────────

async def _handle_client_message(
    websocket: WebSocket,
    video_id: str,
    last_sent: set,
    raw: str,
) -> None:
    """解析并处理单条客户端消息。"""
    if raw == "ping":
        await websocket.send_json({"type": "pong"})
        return

    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        logger.debug("ws/{} 收到非 JSON 消息: {!r}", video_id, raw[:50])
        return

    msg_type = msg.get("type")

    if msg_type == "ping":
        await websocket.send_json({"type": "pong"})

    elif msg_type == "time":
        current_time = float(msg.get("currentTime", 0))
        await _dispatch_timed_danmaku(websocket, video_id, current_time, last_sent)

    else:
        logger.debug("ws/{} 未知消息类型: {}", video_id, msg_type)


# ── 主端点 ────────────────────────────────────────────────────────────────────

@router.websocket("/ws/danmaku/{video_id}")
async def danmaku_websocket(websocket: WebSocket, video_id: str) -> None:
    """
    实时弹幕推送 WebSocket。

    架构：
      ┌─ _heartbeat_task ─────────────────┐  ← 独立协程，每 25s 发 ping
      └─ message loop ────────────────────┘  ← 主协程，处理客户端消息

    客户端可发送：
      {"type": "ping"}                        → 服务端回 pong
      {"type": "time", "currentTime": 12.5}  → 服务端推送对应时间弹幕
    """
    accepted = await manager.connect(video_id, websocket)
    if not accepted:
        return
    poller.start_polling(video_id)

    last_sent: set = set()

    # 启动独立心跳协程，与消息循环并发
    heartbeat = asyncio.create_task(_heartbeat_task(websocket))

    try:
        while True:
            try:
                raw = await websocket.receive_text()
                await _handle_client_message(websocket, video_id, last_sent, raw)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error("ws/{} 异常: {}", video_id, e)
                break
    finally:
        heartbeat.cancel()
        manager.disconnect(video_id, websocket)

        # 无订阅者时停止轮询，释放资源
        if not manager.active_connections.get(video_id):
            poller.stop_polling(video_id)
            logger.info("ws/{} 无订阅者，停止轮询", video_id)