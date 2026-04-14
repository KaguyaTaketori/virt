from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.deps import get_db_session
from app.models.models import User, Channel, UserChannel
from app.schemas.schemas import ChannelResponse
from app.auth import get_current_user
from app.constants import UserChannelStatus

router = APIRouter(prefix="/api/users/channels", tags=["user-channels"])


@router.post("/{channel_id}/like", status_code=status.HTTP_201_CREATED)
async def like_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    result = await db.execute(
        select(UserChannel).where(
            UserChannel.user_id == current_user.id,
            UserChannel.channel_id == channel_id,
            UserChannel.status == UserChannelStatus.LIKED,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {"message": "Channel already liked"}

    result = await db.execute(
        select(UserChannel).where(
            UserChannel.user_id == current_user.id,
            UserChannel.channel_id == channel_id,
            UserChannel.status == UserChannelStatus.BLOCKED,
        )
    )
    existing_blocked = result.scalar_one_or_none()
    if existing_blocked:
        existing_blocked.status = UserChannelStatus.LIKED
    else:
        user_channel = UserChannel(
            user_id=current_user.id, channel_id=channel_id, status=UserChannelStatus.LIKED
        )
        db.add(user_channel)

    await db.commit()
    return {"message": "Channel liked"}


@router.delete("/{channel_id}/like")
async def unlike_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserChannel).where(
            UserChannel.user_id == current_user.id,
            UserChannel.channel_id == channel_id,
            UserChannel.status == UserChannelStatus.LIKED,
        )
    )
    user_channel = result.scalar_one_or_none()
    if not user_channel:
        raise HTTPException(status_code=404, detail="Channel not liked")

    await db.delete(user_channel)
    await db.commit()
    return {"message": "Channel unliked"}


@router.post("/{channel_id}/block", status_code=status.HTTP_201_CREATED)
async def block_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    result = await db.execute(
        select(UserChannel).where(
            UserChannel.user_id == current_user.id,
            UserChannel.channel_id == channel_id,
            UserChannel.status == UserChannelStatus.BLOCKED,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {"message": "Channel already blocked"}

    result = await db.execute(
        select(UserChannel).where(
            UserChannel.user_id == current_user.id,
            UserChannel.channel_id == channel_id,
            UserChannel.status == UserChannelStatus.LIKED,
        )
    )
    existing_liked = result.scalar_one_or_none()
    if existing_liked:
        existing_liked.status = UserChannelStatus.BLOCKED
    else:
        user_channel = UserChannel(
            user_id=current_user.id, channel_id=channel_id, status=UserChannelStatus.BLOCKED
        )
        db.add(user_channel)

    await db.commit()
    return {"message": "Channel blocked"}


@router.delete("/{channel_id}/block")
async def unblock_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserChannel).where(
            UserChannel.user_id == current_user.id,
            UserChannel.channel_id == channel_id,
            UserChannel.status == UserChannelStatus.BLOCKED,
        )
    )
    user_channel = result.scalar_one_or_none()
    if not user_channel:
        raise HTTPException(status_code=404, detail="Channel not blocked")

    await db.delete(user_channel)
    await db.commit()
    return {"message": "Channel unblocked"}


@router.get("", response_model=list[ChannelResponse])
async def get_user_channels(
    type: str = Query(..., pattern="^(liked|blocked)$"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserChannel).where(
            UserChannel.user_id == current_user.id,
            UserChannel.status == type,
        )
    )
    user_channels = result.scalars().all()

    channel_ids = [uc.channel_id for uc in user_channels]
    result = await db.execute(select(Channel).where(Channel.id.in_(channel_ids)))
    channels = result.scalars().all()

    channel_dict = {ch.id: ch for ch in channels}
    result_list = []
    for uc in user_channels:
        ch = channel_dict.get(uc.channel_id)
        if ch:
            response = ChannelResponse.model_validate(ch)
            response.is_liked = uc.status == UserChannelStatus.LIKED
            response.is_blocked = uc.status == UserChannelStatus.BLOCKED
            result_list.append(response)

    return result_list
