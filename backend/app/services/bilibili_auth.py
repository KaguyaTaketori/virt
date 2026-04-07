# backend/app/services/bilibili_auth.py
from __future__ import annotations

import uuid
import asyncio
import base64
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from bilibili_api import Credential, login_v2
from bilibili_api.login_v2 import QrCodeLoginChannel
from app.loguru_config import logger

_SESSION_TTL_SECONDS = 180
_CLEANUP_INTERVAL_SECONDS = 300


class QrCodeStatus(Enum):
    NEW = "new"
    SCANNED = "scanned"
    CONFIRMED = "confirmed"
    TIMEOUT = "timeout"


@dataclass
class QrCodeSession:
    session_id: str
    qrcode_url: str
    login: login_v2.QrCodeLogin
    status: QrCodeStatus = QrCodeStatus.NEW
    credential: Optional[Credential] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_expired(self) -> bool:
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > _SESSION_TTL_SECONDS


class BilibiliAuthService:
    def __init__(self):
        self._sessions: dict[str, QrCodeSession] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def start_cleanup_task(self) -> None:
        """在应用启动时调用一次，启动后台清理协程。"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(
                self._periodic_cleanup(),
                name="bilibili_session_cleanup",
            )
            logger.info("Bilibili session cleanup task started")

    async def _periodic_cleanup(self) -> None:
        while True:
            await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
            try:
                self._evict_expired()
            except Exception as e:
                logger.error("Session cleanup error: {}", e)

    def _evict_expired(self) -> None:
        expired_keys = [
            sid for sid, sess in self._sessions.items()
            if sess.is_expired() or sess.status in (QrCodeStatus.CONFIRMED, QrCodeStatus.TIMEOUT)
        ]
        for key in expired_keys:
            del self._sessions[key]
        if expired_keys:
            logger.debug("Evicted {} expired Bilibili sessions", len(expired_keys))

    async def generate_qrcode(self) -> dict:
        self._evict_expired()

        session_id = str(uuid.uuid4())
        login = login_v2.QrCodeLogin(platform=QrCodeLoginChannel.WEB)
        await login.generate_qrcode()

        picture = login.get_qrcode_picture()
        qrcode_url = "data:image/png;base64," + base64.b64encode(picture.content).decode()

        session = QrCodeSession(
            session_id=session_id,
            qrcode_url=qrcode_url,
            login=login,
        )
        self._sessions[session_id] = session
        logger.info("Generated QR code, session_id={}, active_sessions={}",
                    session_id, len(self._sessions))

        return {"session_id": session_id, "qrcode_url": qrcode_url}

    async def check_status(self, session_id: str) -> dict:
        session = self._sessions.get(session_id)
        if not session:
            return {"status": "not_found", "message": "Session not found or expired"}

        if session.is_expired() and session.status == QrCodeStatus.NEW:
            session.status = QrCodeStatus.TIMEOUT
            return {"status": "timeout", "message": "QR code expired"}

        try:
            await session.login.check_state()
        except Exception as e:
            logger.warning("QR check failed session_id={}: {}", session_id, e)
            return {"status": "error", "message": str(e)}

        if session.login.has_done():
            session.status = QrCodeStatus.CONFIRMED
            try:
                session.credential = session.login.get_credential()
                return {
                    "status": "confirmed",
                    "credential": {
                        "sessdata": session.credential.sessdata,
                        "bili_jct": session.credential.bili_jct,
                        "buvid3": session.credential.buvid3,
                        "dedeuserid": session.credential.dedeuserid,
                    },
                }
            except Exception as e:
                return {"status": "error", "message": f"Failed to get credential: {e}"}

        if not session.login.has_qrcode():
            session.status = QrCodeStatus.TIMEOUT
            return {"status": "timeout", "message": "QR code expired"}

        session.status = QrCodeStatus.SCANNED
        return {"status": "scanned", "message": "Please confirm on device"}


bilibili_auth_service = BilibiliAuthService()