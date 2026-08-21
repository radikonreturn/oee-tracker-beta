from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import DowntimeCategory, DowntimeReason
from schemas import DowntimeReasonCreate, DowntimeReasonRead, DowntimeReasonUpdate

router = APIRouter(prefix="/downtime-reasons", tags=["Downtime Reasons"])


@router.post("/", response_model=DowntimeReasonRead, status_code=status.HTTP_201_CREATED)
def create_downtime_reason(
    payload: DowntimeReasonCreate, db: Session = Depends(get_db)
):
    existing = db.scalar(
        select(DowntimeReason).where(DowntimeReason.name == payload.name)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Downtime reason '{payload.name}' already exists.",
        )
    reason = DowntimeReason(**payload.model_dump())
    db.add(reason)
    db.commit()
    db.refresh(reason)
    return reason


@router.get("/", response_model=List[DowntimeReasonRead])
def list_downtime_reasons(
    category: Optional[DowntimeCategory] = None,
    is_planned: Optional[bool] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    stmt = select(DowntimeReason).order_by(DowntimeReason.name)
    if category is not None:
        stmt = stmt.where(DowntimeReason.category == category)
    if is_planned is not None:
        stmt = stmt.where(DowntimeReason.is_planned == is_planned)
    if is_active is not None:
        stmt = stmt.where(DowntimeReason.is_active == is_active)
    return list(db.scalars(stmt).all())


@router.get("/{reason_id}", response_model=DowntimeReasonRead)
def get_downtime_reason(reason_id: int, db: Session = Depends(get_db)):
    reason = db.get(DowntimeReason, reason_id)
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Downtime reason with id {reason_id} not found.",
        )
    return reason


@router.put("/{reason_id}", response_model=DowntimeReasonRead)
def update_downtime_reason(
    reason_id: int,
    payload: DowntimeReasonUpdate,
    db: Session = Depends(get_db),
):
    reason = db.get(DowntimeReason, reason_id)
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Downtime reason with id {reason_id} not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] != reason.name:
        duplicate = db.scalar(
            select(DowntimeReason).where(DowntimeReason.name == update_data["name"])
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Downtime reason '{update_data['name']}' already exists.",
            )

    for field, value in update_data.items():
        setattr(reason, field, value)

    db.commit()
    db.refresh(reason)
    return reason


@router.delete("/{reason_id}", response_model=DowntimeReasonRead)
def delete_downtime_reason(reason_id: int, db: Session = Depends(get_db)):
    reason = db.get(DowntimeReason, reason_id)
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Downtime reason with id {reason_id} not found.",
        )
    reason.is_active = False
    db.commit()
    db.refresh(reason)
    return reason
