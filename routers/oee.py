from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import Machine, Shift
from oee_service import OEEMetrics, calculate_dashboard_oee, calculate_machine_oee

router = APIRouter(prefix="/oee", tags=["OEE Analytics"])


@router.get("/machine", response_model=OEEMetrics)
def get_machine_oee(
    machine_id: int = Query(..., description="ID of the machine"),
    start_time: datetime = Query(..., description="Start of evaluation window"),
    end_time: datetime = Query(..., description="End of evaluation window"),
    shift_id: Optional[int] = Query(None, description="Optional shift ID filter"),
    db: Session = Depends(get_db),
):
    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be strictly greater than start_time.",
        )

    if not db.get(Machine, machine_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found.",
        )

    if shift_id and not db.get(Shift, shift_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with id {shift_id} not found.",
        )

    return calculate_machine_oee(
        session=db,
        machine_id=machine_id,
        start_time=start_time,
        end_time=end_time,
        shift_id=shift_id,
    )


@router.get("/dashboard", response_model=List[OEEMetrics])
def get_dashboard_oee(
    start_time: datetime = Query(..., description="Start of evaluation window"),
    end_time: datetime = Query(..., description="End of evaluation window"),
    machine_ids: Optional[str] = Query(
        None, description="Comma-separated machine IDs, e.g. '1,2,3'"
    ),
    shift_id: Optional[int] = Query(None, description="Optional shift ID filter"),
    db: Session = Depends(get_db),
):
    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be strictly greater than start_time.",
        )

    if shift_id and not db.get(Shift, shift_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with id {shift_id} not found.",
        )

    parsed_ids: Optional[List[int]] = None
    if machine_ids:
        try:
            parsed_ids = [
                int(mid.strip()) for mid in machine_ids.split(",") if mid.strip()
            ]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="machine_ids must be a comma-separated list of integers.",
            )

    return calculate_dashboard_oee(
        session=db,
        start_time=start_time,
        end_time=end_time,
        machine_ids=parsed_ids,
        shift_id=shift_id,
    )
