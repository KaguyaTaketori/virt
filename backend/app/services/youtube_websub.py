from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from typing import Optional

from app.config import settings
from app.loguru_config import logger
from app.deps.guards import AdminUser, validate_websub_callback
from app.models.models import User

from app.integrations.websub.subscription_service import websub_service
from app.services.websub.atom_parser import parse_atom_feed
from app.integrations.websub.security import verify_hmac_signature


router = APIRouter(prefix="/api/websub", tags=["websub"])
_TOPIC_BASE = ".xml?channel_id="


# Backward compatibility alias
async def subscribe_all_active_channels(callback_url: str, secret: str = "") -> None:
    """Legacy alias for subscribe_all_active"""
    await websub_service.subscribe_all_active(callback_url, secret=secret)


@router.get("/youtube", response_class=PlainTextResponse)
async def websub_verify(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_topic: str = Query(..., alias="hub.topic"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_lease_seconds: Optional[int] = Query(None, alias="hub.lease_seconds"),
) -> PlainTextResponse:
    if hub_mode not in ("subscribe", "unsubscribe") or not hub_topic.startswith(
        _TOPIC_BASE
    ):
        raise HTTPException(status_code=404)

    yt_channel_id = hub_topic.removeprefix(_TOPIC_BASE)
    await websub_service.confirm_verification(yt_channel_id, hub_mode)

    return PlainTextResponse(hub_challenge)


@router.post("/youtube")
async def websub_receive(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature: Optional[str] = Header(None, alias="X-Hub-Signature"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
) -> dict:
    raw_body = await request.body()

    if not verify_hmac_signature(
        raw_body,
        x_hub_signature,
        settings.websub_secret,
        preferred_header=x_hub_signature_256,
    ):
        raise HTTPException(status_code=403, detail="Signature invalid")

    entries = parse_atom_feed(raw_body)
    if not entries:
        return {"ok": True, "processed": 0}

    for entry in entries:
        background_tasks.add_task(
            websub_service.process_video_notification,
            entry["channel_id"],
            entry["video_id"],
        )

    return {"ok": True, "processed": len(entries)}


@router.post("/youtube/subscribe/{channel_db_id}")
async def manual_subscribe(
    channel_db_id: int,
    callback_url: str = Query(..., description="公网回调 URL"),
    _: User = AdminUser,
) -> dict:
    validated_callback = validate_websub_callback(
        callback_url, settings.websub_callback_url
    )

    ok = await websub_service.subscribe_channel(
        channel_db_id, validated_callback, secret=settings.websub_secret
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Hub request failed")
    return {"ok": True}


@router.post("/youtube/subscribe-all")
async def bulk_subscribe(
    callback_url: str = Query(..., description="公网回调 URL"),
    _: User = AdminUser,
) -> dict:
    safe_callback = settings.websub_callback_url
    await websub_service.subscribe_all_active(
        safe_callback, secret=settings.websub_secret
    )
    return {"ok": True}
