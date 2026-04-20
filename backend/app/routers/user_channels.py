from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session, get_channel_repo, get_user_channel_repo
from app.models.models import User
from app.schemas.schemas import ChannelResponse
from app.auth import get_current_user
from app.constants import UserChannelStatus
from app.repositories import ChannelRepository, UserChannelRepository

router = APIRouter(prefix="/api/users/channels", tags=["user-channels"])


@router.post("/{channel_id}/like", status_code=status.HTTP_201_CREATED)
async def like_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    channel_repo: ChannelRepository = Depends(get_channel_repo),
    user_channel_repo: UserChannelRepository = Depends(get_user_channel_repo),
):
    channel = await channel_repo.get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    existing = await user_channel_repo.get_by_user_channel_and_status(
        current_user.id, channel_id, UserChannelStatus.LIKED
    )
    if existing:
        return {"message": "Channel already liked"}

    existing_blocked = await user_channel_repo.get_by_user_channel_and_status(
        current_user.id, channel_id, UserChannelStatus.BLOCKED
    )
    if existing_blocked:
        existing_blocked.status = UserChannelStatus.LIKED
    else:
        user_channel = user_channel_repo.model(
            user_id=current_user.id,
            channel_id=channel_id,
            status=UserChannelStatus.LIKED,
        )
        db.add(user_channel)

    await db.commit()
    return {"message": "Channel liked"}


@router.delete("/{channel_id}/like")
async def unlike_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    user_channel_repo: UserChannelRepository = Depends(get_user_channel_repo),
):
    user_channel = await user_channel_repo.get_by_user_channel_and_status(
        current_user.id, channel_id, UserChannelStatus.LIKED
    )
    if not user_channel:
        raise HTTPException(status_code=404, detail="Channel not liked")

    await user_channel_repo.remove(user_channel.id)
    await db.commit()
    return {"message": "Channel unliked"}


@router.post("/{channel_id}/block", status_code=status.HTTP_201_CREATED)
async def block_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    channel_repo: ChannelRepository = Depends(get_channel_repo),
    user_channel_repo: UserChannelRepository = Depends(get_user_channel_repo),
):
    channel = await channel_repo.get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    existing = await user_channel_repo.get_by_user_channel_and_status(
        current_user.id, channel_id, UserChannelStatus.BLOCKED
    )
    if existing:
        return {"message": "Channel already blocked"}

    existing_liked = await user_channel_repo.get_by_user_channel_and_status(
        current_user.id, channel_id, UserChannelStatus.LIKED
    )
    if existing_liked:
        existing_liked.status = UserChannelStatus.BLOCKED
    else:
        user_channel = user_channel_repo.model(
            user_id=current_user.id,
            channel_id=channel_id,
            status=UserChannelStatus.BLOCKED,
        )
        db.add(user_channel)

    await db.commit()
    return {"message": "Channel blocked"}


@router.delete("/{channel_id}/block")
async def unblock_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    user_channel_repo: UserChannelRepository = Depends(get_user_channel_repo),
):
    user_channel = await user_channel_repo.get_by_user_channel_and_status(
        current_user.id, channel_id, UserChannelStatus.BLOCKED
    )
    if not user_channel:
        raise HTTPException(status_code=404, detail="Channel not blocked")

    await user_channel_repo.remove(user_channel.id)
    await db.commit()
    return {"message": "Channel unblocked"}


@router.get("", response_model=list[ChannelResponse])
async def get_user_channels(
    type: str = Query(..., pattern="^(liked|blocked)$"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    channel_repo: ChannelRepository = Depends(get_channel_repo),
    user_channel_repo: UserChannelRepository = Depends(get_user_channel_repo),
):
    user_channels = await user_channel_repo.get_by_user_and_status(
        current_user.id, type
    )

    channel_ids = [uc.channel_id for uc in user_channels]
    channels = await channel_repo.get_multi_by_ids(channel_ids)

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
