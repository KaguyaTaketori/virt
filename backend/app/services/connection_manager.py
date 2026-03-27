from typing import Dict, List
from fastapi import WebSocket
import asyncio
import json


class ConnectionManager:
    """管理WebSocket连接，支持按video_id分组"""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, video_id: str, websocket: WebSocket):
        """客户端连接"""
        await websocket.accept()
        if video_id not in self.active_connections:
            self.active_connections[video_id] = []
        self.active_connections[video_id].append(websocket)

    def disconnect(self, video_id: str, websocket: WebSocket):
        """客户端断开"""
        if video_id in self.active_connections:
            if websocket in self.active_connections[video_id]:
                self.active_connections[video_id].remove(websocket)
            if not self.active_connections[video_id]:
                del self.active_connections[video_id]

    async def send_message(self, video_id: str, message: dict):
        """向指定video_id的所有连接发送消息"""
        if video_id not in self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections[video_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for ws in disconnected:
            self.disconnect(video_id, ws)

    async def broadcast(self, message: dict):
        """广播消息到所有连接"""
        for video_id in list(self.active_connections.keys()):
            await self.send_message(video_id, message)


manager = ConnectionManager()
