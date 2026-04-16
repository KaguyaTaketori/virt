from typing import Dict, List
from fastapi import WebSocket
import asyncio
import json

from app.config import settings
from app.loguru_config import logger

_MAX_CONNECTIONS_PER_VIDEO = settings.max_ws_connections_per_video
_MAX_TOTAL_CONNECTIONS = settings.max_ws_connections_total


class ConnectionManager:
    """管理WebSocket连接，支持按video_id分组"""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    @property
    def total_connections(self) -> int:
        """计算全局所有视频的总连接数"""
        return sum(len(connections) for connections in self.active_connections.values())

    async def connect(self, video_id: str, websocket: WebSocket) -> bool:
        # 全局连接数保护
        if self.total_connections >= _MAX_TOTAL_CONNECTIONS:
            logger.warning(
                "Global WebSocket connection limit reached: {}/{}",
                self.total_connections, _MAX_TOTAL_CONNECTIONS,
            )
            await websocket.close(code=1013, reason="Server at capacity")
            return False

        # 单 video 连接数保护
        video_conns = self.active_connections.get(video_id, [])
        if len(video_conns) >= _MAX_CONNECTIONS_PER_VIDEO:
            logger.warning(
                "Per-video WebSocket limit reached for {}: {}/{}",
                video_id, len(video_conns), _MAX_CONNECTIONS_PER_VIDEO,
            )
            await websocket.close(code=1013, reason="Too many viewers for this stream")
            return False

        await websocket.accept()
        if video_id not in self.active_connections:
            self.active_connections[video_id] = []
        self.active_connections[video_id].append(websocket)
        return True
    
    def disconnect(self, video_id: str, websocket: WebSocket):
        """客户端断开"""
        if video_id in self.active_connections:
            if websocket in self.active_connections[video_id]:
                self.active_connections[video_id].remove(websocket)
            if not self.active_connections[video_id]:
                del self.active_connections[video_id]

    async def send_message(self, video_id: str, message: dict) -> int:
        connections = self.active_connections.get(video_id)
        if not connections:
            return 0

        results = await asyncio.gather(
            *[conn.send_json(message) for conn in list(connections)],
            return_exceptions=True,
        )
        
        failed = [
            conn for conn, result in zip(list(connections), results)
            if isinstance(result, Exception)
        ]
        for ws in failed:
            self.disconnect(video_id, ws)
        
        return len(connections) - len(failed)

    async def broadcast(self, message: dict) -> None:
        for video_id in list(self.active_connections.keys()):
            await self.send_message(video_id, message)


manager = ConnectionManager()
