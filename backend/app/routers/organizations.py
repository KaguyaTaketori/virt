from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.deps import get_db_session, get_organization_repo
from app.deps.guards import AdminUser
from app.models.models import User
from app.schemas.schemas import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.repositories import OrganizationRepository

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.get("", response_model=List[OrganizationResponse])
async def get_organizations(
    org_repo: OrganizationRepository = Depends(get_organization_repo),
):
    return await org_repo.get_multi()


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: int,
    org_repo: OrganizationRepository = Depends(get_organization_repo),
):
    org = await org_repo.get(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.post("", response_model=OrganizationResponse)
async def create_organization(
    org: OrganizationCreate,
    db: AsyncSession = Depends(get_db_session),
    org_repo: OrganizationRepository = Depends(get_organization_repo),
    _current_user: User = AdminUser,
):
    existing = await org_repo.get_by_name(org.name)
    if existing:
        raise HTTPException(status_code=400, detail="Organization already exists")

    db_org = await org_repo.create(org.model_dump())
    return db_org


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: int,
    org_update: OrganizationUpdate,
    db: AsyncSession = Depends(get_db_session),
    org_repo: OrganizationRepository = Depends(get_organization_repo),
    _: User = AdminUser,
):
    org = await org_repo.get(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    update_data = org_update.model_dump(exclude_unset=True)
    if update_data:
        org = await org_repo.update(org_id, update_data)

    return org


@router.delete("/{org_id}")
async def delete_organization(
    org_id: int,
    db: AsyncSession = Depends(get_db_session),
    org_repo: OrganizationRepository = Depends(get_organization_repo),
    _current_user: User = AdminUser,
):
    org = await org_repo.get_with_channels(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    for channel in org.channels:
        channel.org_id = None

    await org_repo.remove(org_id)
    await db.commit()
    return {"message": "Organization deleted successfully"}
