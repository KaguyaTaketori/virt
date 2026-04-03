from __future__ import annotations
from typing import AsyncGenerator, Generator
from fastapi import Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database_async import AsyncSessionFactory
    
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

def get_db() -> Generator[Session, None, None]:
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_admin_key(x_admin_key: str = Header(default=None)) -> None:
    if not settings.admin_secret_key:
        return
    if x_admin_key != settings.admin_secret_key:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key header")