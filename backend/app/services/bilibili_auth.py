from __future__ import annotations

import base64
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from bilibili_api import Credential, login_v2
from bilibili_api.login_v2 import QrCodeLoginChannel

from app.loguru_config import logger


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


class BilibiliAuthService:
    _sessions: dict[str, QrCodeSession] = {}

    @classmethod
    async def generate_qrcode(cls) -> dict:
        import uuid
        import base64

        session_id = str(uuid.uuid4())
        login = login_v2.QrCodeLogin(platform=QrCodeLoginChannel.WEB)

        await login.generate_qrcode()
        picture = login.get_qrcode_picture()

        qrcode_data = base64.b64encode(picture.content).decode("utf-8")
        qrcode_url = f"data:image/png;base64,{qrcode_data}"

        session = QrCodeSession(
            session_id=session_id,
            qrcode_url=qrcode_url,
            login=login,
            status=QrCodeStatus.NEW,
        )
        cls._sessions[session_id] = session

        logger.info("Generated QR code, session_id={}", session_id)

        return {
            "session_id": session_id,
            "qrcode_url": qrcode_url,
        }

    @classmethod
    async def check_status(cls, session_id: str) -> dict:
        session = cls._sessions.get(session_id)
        if not session:
            return {"status": "not_found", "message": "Session not found"}

        try:
            await session.login.check_state()
        except Exception as e:
            logger.warning("QR code check failed, session_id={}: {}", session_id, e)
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
                logger.error(
                    "Failed to get credential, session_id={}: {}", session_id, e
                )
                return {"status": "error", "message": f"Failed to get credential: {e}"}

        if not session.login.has_qrcode():
            session.status = QrCodeStatus.TIMEOUT
            return {"status": "timeout", "message": "QR code expired"}

        session.status = QrCodeStatus.SCANNED
        return {"status": "scanned", "message": "Please confirm on device"}

    @classmethod
    def get_credential(cls, session_id: str) -> Optional[Credential]:
        session = cls._sessions.get(session_id)
        if session and session.credential:
            return session.credential
        return None


bilibili_auth_service = BilibiliAuthService()
