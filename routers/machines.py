from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Machine
from schemas import MachineCreate, MachineRead, MachineUpdate

router = APIRouter(prefix="/machines", tags=["Machines"])


@router.post("/", response_model=MachineRead, status_code=status.HTTP_201_CREATED)
def create_machine(payload: MachineCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(Machine).where(Machine.code == payload.code))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Machine with code '{payload.code}' already exists.",
        )
    machine = Machine(**payload.model_dump())
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine


@router.get("/", response_model=List[MachineRead])
def list_machines(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    stmt = select(Machine).order_by(Machine.name)
    if is_active is not None:
        stmt = stmt.where(Machine.is_active == is_active)
    return list(db.scalars(stmt).all())


@router.get("/{machine_id}", response_model=MachineRead)
def get_machine(machine_id: int, db: Session = Depends(get_db)):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found.",
        )
    return machine


@router.put("/{machine_id}", response_model=MachineRead)
def update_machine(
    machine_id: int,
    payload: MachineUpdate,
    db: Session = Depends(get_db),
):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "code" in update_data and update_data["code"] != machine.code:
        duplicate = db.scalar(select(Machine).where(Machine.code == update_data["code"]))
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Machine with code '{update_data['code']}' already exists.",
            )

    for field, value in update_data.items():
        setattr(machine, field, value)

    db.commit()
    db.refresh(machine)
    return machine


@router.delete("/{machine_id}", response_model=MachineRead)
def delete_machine(machine_id: int, db: Session = Depends(get_db)):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found.",
        )
    machine.is_active = False
    db.commit()
    db.refresh(machine)
    return machine
