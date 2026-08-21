from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from database import get_db
from models import Machine, ProductionRun, Shift
from schemas import ProductionRunCreate, ProductionRunRead, ProductionRunUpdate

router = APIRouter(prefix="/production-runs", tags=["Production Runs"])


@router.post("/", response_model=ProductionRunRead, status_code=status.HTTP_201_CREATED)
def create_production_run(payload: ProductionRunCreate, db: Session = Depends(get_db)):
    if not db.get(Machine, payload.machine_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {payload.machine_id} does not exist.",
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
    if payload.scrap_units > payload.total_units:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scrap_units cannot exceed total_units.",
        )

    run = ProductionRun(**payload.model_dump())
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/", response_model=List[ProductionRunRead])
def list_production_runs(
    machine_id: Optional[int] = None,
    shift_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    stmt = select(ProductionRun).order_by(ProductionRun.start_time.desc())
    if machine_id is not None:
        stmt = stmt.where(ProductionRun.machine_id == machine_id)
    if shift_id is not None:
        stmt = stmt.where(ProductionRun.shift_id == shift_id)
    if start_time is not None:
        stmt = stmt.where(
            or_(ProductionRun.end_time.is_(None), ProductionRun.end_time >= start_time)
        )
    if end_time is not None:
        stmt = stmt.where(ProductionRun.start_time <= end_time)

    return list(db.scalars(stmt).all())


@router.get("/{run_id}", response_model=ProductionRunRead)
def get_production_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(ProductionRun, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production run with id {run_id} not found.",
        )
    return run


@router.put("/{run_id}", response_model=ProductionRunRead)
def update_production_run(
    run_id: int,
    payload: ProductionRunUpdate,
    db: Session = Depends(get_db),
):
    run = db.get(ProductionRun, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production run with id {run_id} not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    target_start = update_data.get("start_time", run.start_time)
    target_end = update_data.get("end_time", run.end_time)
    if target_end is not None and target_end <= target_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be strictly greater than start_time.",
        )

    target_total = update_data.get("total_units", run.total_units)
    target_scrap = update_data.get("scrap_units", run.scrap_units)
    if target_scrap > target_total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scrap_units cannot exceed total_units.",
        )

    if "machine_id" in update_data and not db.get(Machine, update_data["machine_id"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {update_data['machine_id']} does not exist.",
        )
    if update_data.get("shift_id") and not db.get(Shift, update_data["shift_id"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with id {update_data['shift_id']} does not exist.",
        )

    for field, value in update_data.items():
        setattr(run, field, value)

    db.commit()
    db.refresh(run)
    return run
