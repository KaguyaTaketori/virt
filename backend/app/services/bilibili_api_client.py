from bilibili_api import user, Credential
from typing import Optional
import asyncio

from app.services.bilibili_constants import BACKOFF_INIT, BACKOFF_MAX, MAX_RETRIES

class BilibiliApiClient:
    """只负责与 Bilibili API 通信，返回原始 dict。"""
    async def fetch_user_info(self, uid: str, credential: Credential) -> Optional[dict]:
        u = user.User(uid=int(uid), credential=credential)
        return await u.get_user_info()

    async def fetch_dynamics(
        self, uid: str, credential: Credential, offset: str = ""
    ) -> dict:
        u = user.User(uid=int(uid), credential=credential)
        return await u.get_dynamics_new(offset=offset)

    async def fetch_videos(
        self, uid: str, credential: Credential, page: int, page_size: int
    ) -> dict:
        """带退避重试的视频拉取。"""
        backoff = BACKOFF_INIT
        for attempt in range(MAX_RETRIES):
            try:
                u = user.User(uid=int(uid), credential=credential)
                return await u.get_videos(pn=page, ps=page_size)
            except Exception as e:
                if "412" in str(e):
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, BACKOFF_MAX)
                else:
                    raise
        raise RuntimeError(f"uid={uid} 视频获取重试耗尽")
