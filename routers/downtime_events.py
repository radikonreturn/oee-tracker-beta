from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import DowntimeEvent, DowntimeReason, Machine, Shift
from schemas import DowntimeEventCreate, DowntimeEventRead, DowntimeEventUpdate

router = APIRouter(prefix="/downtime-events", tags=["Downtime Events"])


@router.post("/", response_model=DowntimeEventRead, status_code=status.HTTP_201_CREATED)
def create_downtime_event(payload: DowntimeEventCreate, db: Session = Depends(get_db)):
    if not db.get(Machine, payload.machine_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {payload.machine_id} does not exist.",
        )
    if not db.get(DowntimeReason, payload.reason_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Downtime reason with id {payload.reason_id} does not exist.",
        )
    if payload.shift_id and not db.get(Shift, payload.shift_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with id {payload.shift_id} does not exist.",
        )
    if payload.end_time and payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be strictly greater than start_time.",
        )

    event = DowntimeEvent(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/", response_model=List[DowntimeEventRead])
def list_downtime_events(
    machine_id: Optional[int] = None,
    shift_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    stmt = (
        select(DowntimeEvent)
        .options(joinedload(DowntimeEvent.reason))
        .order_by(DowntimeEvent.start_time.desc())
    )
    if machine_id is not None:
        stmt = stmt.where(DowntimeEvent.machine_id == machine_id)
    if shift_id is not None:
        stmt = stmt.where(DowntimeEvent.shift_id == shift_id)
    if start_time is not None:
        stmt = stmt.where(
            or_(DowntimeEvent.end_time.is_(None), DowntimeEvent.end_time >= start_time)
        )
    if end_time is not None:
        stmt = stmt.where(DowntimeEvent.start_time <= end_time)

    return list(db.scalars(stmt).all())


@router.get("/{event_id}", response_model=DowntimeEventRead)
def get_downtime_event(event_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(DowntimeEvent)
        .options(joinedload(DowntimeEvent.reason))
        .where(DowntimeEvent.id == event_id)
    )
    event = db.scalar(stmt)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Downtime event with id {event_id} not found.",
        )
    return event


@router.put("/{event_id}", response_model=DowntimeEventRead)
def update_downtime_event(
    event_id: int,
    payload: DowntimeEventUpdate,
    db: Session = Depends(get_db),
):
    event = db.get(DowntimeEvent, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Downtime event with id {event_id} not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    target_start = update_data.get("start_time", event.start_time)
    target_end = update_data.get("end_time", event.end_time)

    if target_end is not None and target_end <= target_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be strictly greater than start_time.",
        )

    if "machine_id" in update_data and not db.get(Machine, update_data["machine_id"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {update_data['machine_id']} does not exist.",
        )
    if "reason_id" in update_data and not db.get(DowntimeReason, update_data["reason_id"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Downtime reason with id {update_data['reason_id']} does not exist.",
        )
    if update_data.get("shift_id") and not db.get(Shift, update_data["shift_id"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with id {update_data['shift_id']} does not exist.",
        )

    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return event
