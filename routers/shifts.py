from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Shift
from schemas import ShiftCreate, ShiftRead, ShiftUpdate

router = APIRouter(prefix="/shifts", tags=["Shifts"])


@router.post("/", response_model=ShiftRead, status_code=status.HTTP_201_CREATED)
def create_shift(payload: ShiftCreate, db: Session = Depends(get_db)):
    shift = Shift(**payload.model_dump())
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


@router.get("/", response_model=List[ShiftRead])
def list_shifts(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    stmt = select(Shift).order_by(Shift.start_time)
    if is_active is not None:
        stmt = stmt.where(Shift.is_active == is_active)
    return list(db.scalars(stmt).all())


@router.get("/{shift_id}", response_model=ShiftRead)
def get_shift(shift_id: int, db: Session = Depends(get_db)):
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with id {shift_id} not found.",
        )
    return shift


@router.put("/{shift_id}", response_model=ShiftRead)
def update_shift(
    shift_id: int,
    payload: ShiftUpdate,
    db: Session = Depends(get_db),
):
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with id {shift_id} not found.",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(shift, field, value)

    db.commit()
    db.refresh(shift)
    return shift


@router.delete("/{shift_id}", response_model=ShiftRead)
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with id {shift_id} not found.",
        )
    shift.is_active = False
    db.commit()
    db.refresh(shift)
    return shift
