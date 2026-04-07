from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.deps import get_db_session
from app.deps.guards import AdminUser
from app.models.models import Organization, User
from app.schemas.schemas import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.get("", response_model=List[OrganizationResponse])
async def get_organizations(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Organization))
    return result.scalars().all()


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(org_id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.post("", response_model=OrganizationResponse)
async def create_organization(
    org: OrganizationCreate,
    db: AsyncSession = Depends(get_db_session),
    _current_user: User = AdminUser,
):
    result = await db.execute(select(Organization).where(Organization.name == org.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Organization already exists")
    db_org = Organization(**org.model_dump())
    db.add(db_org)
    await db.commit()
    await db.refresh(db_org)
    return db_org


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: int,
    org_update: OrganizationUpdate,
    db: AsyncSession = Depends(get_db_session),
    _: User = AdminUser,
):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    for key, value in org_update.model_dump(exclude_unset=True).items():
        setattr(org, key, value)

    await db.commit()
    await db.refresh(org)
    return org


@router.delete("/{org_id}")
async def delete_organization(
    org_id: int,
    db: AsyncSession = Depends(get_db_session),
    _current_user: User = AdminUser,
):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    for channel in org.channels:
        channel.org_id = None

    await db.delete(org)
    await db.commit()
    return {"message": "Organization deleted successfully"}
