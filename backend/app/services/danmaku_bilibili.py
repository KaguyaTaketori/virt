import httpx
from app.config import settings

BILIBILI_API_BASE = "https://api.bilibili.com"


async def get_bilibili_danmaku(room_id: str) -> list:
    """获取B站直播弹幕"""
    if not settings.enable_danmaku:
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BILIBILI_API_BASE}/xlive/web-room/v1/dm/getDMSegList",
                params={
                    "type": 1,
                    "oid": room_id,
                    "segment_index": 1,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                return []

            msgs = data.get("data", {}).get("seg", {}).get("data", [])
            return [
                {
                    "content": m.get("content", ""),
                    "progress": m.get("progress", 0),
                    "mode": m.get("mode", 1),
                    "color": m.get("color", "white"),
                }
                for m in msgs
                if m.get("content")
            ]
    except Exception:
        return []
