from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import User, Channel, UserChannel
from app.schemas.schemas import ChannelResponse
from app.auth import get_current_user, get_db

router = APIRouter(prefix="/api/users/channels", tags=["user-channels"])


@router.post("/{channel_id}/like", status_code=status.HTTP_201_CREATED)
async def like_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    existing = (
        db.query(UserChannel)
        .filter(
            UserChannel.user_id == current_user.id,
            UserChannel.channel_id == channel_id,
            UserChannel.status == "liked",
        )
        .first()
    )
    if existing:
        return {"message": "Channel already liked"}

    existing_blocked = (
        db.query(UserChannel)
        .filter(
            UserChannel.user_id == current_user.id,
            UserChannel.channel_id == channel_id,
            UserChannel.status == "blocked",
        )
        .first()
    )
    if existing_blocked:
        existing_blocked.status = "liked"
    else:
        user_channel = UserChannel(
            user_id=current_user.id, channel_id=channel_id, status="liked"
        )
        db.add(user_channel)

    db.commit()
    return {"message": "Channel liked"}


@router.delete("/{channel_id}/like")
async def unlike_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_channel = (
        db.query(UserChannel)
        .filter(
            UserChannel.user_id == current_user.id,
            UserChannel.channel_id == channel_id,
            UserChannel.status == "liked",
        )
        .first()
    )
    if not user_channel:
        raise HTTPException(status_code=404, detail="Channel not liked")

    db.delete(user_channel)
    db.commit()
    return {"message": "Channel unliked"}


@router.post("/{channel_id}/block", status_code=status.HTTP_201_CREATED)
async def block_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    existing = (
        db.query(UserChannel)
        .filter(
            UserChannel.user_id == current_user.id,
            UserChannel.channel_id == channel_id,
            UserChannel.status == "blocked",
        )
        .first()
    )
    if existing:
        return {"message": "Channel already blocked"}

    existing_liked = (
        db.query(UserChannel)
        .filter(
            UserChannel.user_id == current_user.id,
            UserChannel.channel_id == channel_id,
            UserChannel.status == "liked",
        )
        .first()
    )
    if existing_liked:
        existing_liked.status = "blocked"
    else:
        user_channel = UserChannel(
            user_id=current_user.id, channel_id=channel_id, status="blocked"
        )
        db.add(user_channel)

    db.commit()
    return {"message": "Channel blocked"}


@router.delete("/{channel_id}/block")
async def unblock_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_channel = (
        db.query(UserChannel)
        .filter(
            UserChannel.user_id == current_user.id,
            UserChannel.channel_id == channel_id,
            UserChannel.status == "blocked",
        )
        .first()
    )
    if not user_channel:
        raise HTTPException(status_code=404, detail="Channel not blocked")

    db.delete(user_channel)
    db.commit()
    return {"message": "Channel unblocked"}


@router.get("", response_model=list[ChannelResponse])
async def get_user_channels(
    type: str = Query(..., regex="^(liked|blocked)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_channels = (
        db.query(UserChannel)
        .filter(
            UserChannel.user_id == current_user.id,
            UserChannel.status == type,
        )
        .all()
    )

    channel_ids = [uc.channel_id for uc in user_channels]
    channels = db.query(Channel).filter(Channel.id.in_(channel_ids)).all()

    channel_dict = {ch.id: ch for ch in channels}
    result = []
    for uc in user_channels:
        ch = channel_dict.get(uc.channel_id)
        if ch:
            response = ChannelResponse.model_validate(ch)
            response.is_liked = uc.status == "liked"
            response.is_blocked = uc.status == "blocked"
            result.append(response)

    return result
