from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.deps import get_db
from app.schemas.schemas import OrganizationCreate, OrganizationResponse, OrganizationUpdate
from app.models.models import Organization, User
from app.auth import get_current_user
from app.services.permissions import require_admin
from app.services.permissions import get_user_roles

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.get("", response_model=List[OrganizationResponse])
def get_organizations(db: Session = Depends(get_db)):
    return db.query(Organization).all()


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(org_id: int, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org



@router.post("", response_model=OrganizationResponse)
def create_organization(
    org: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(db, current_user)                   
    if db.query(Organization).filter(Organization.name == org.name).first():
        raise HTTPException(status_code=400, detail="Organization already exists")
    db_org = Organization(**org.model_dump())
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org


@router.put("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: int,
    org_update: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(db, current_user)
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    for key, value in org_update.model_dump(exclude_unset=True).items():
        setattr(org, key, value)
    db.commit()
    db.refresh(org)
    return org


@router.delete("/{org_id}")
def delete_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(db, current_user)
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    for channel in org.channels:
        channel.org_id = None
    db.delete(org)
    db.commit()
    return {"message": "Organization deleted successfully"}