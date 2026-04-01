# backend/app/deps.py
"""
全局依赖注入模块。

所有 Router 统一从此处导入，禁止在各 Router 文件中重复定义。
"""
from __future__ import annotations

from typing import Generator, Optional

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal


# ── 数据库 Session ────────────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """
    同步数据库 Session 依赖注入。

    使用方式：
        @router.get("/")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_admin_key(x_admin_key: str = Header(default=None)) -> None:
    """
    静态 API Key 验证。
    未配置 admin_secret_key 时跳过验证（开发模式）。
    生产环境必须在 .env 里配置，否则任何人都能触发管理接口。
    """
    if not settings.admin_secret_key:
        return
    if x_admin_key != settings.admin_secret_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing X-Admin-Key header",
        )