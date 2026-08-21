from datetime import datetime, time, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import DowntimeEvent, DowntimeReason, Machine, ProductionRun, Shift
from oee_service import calculate_dashboard_oee, calculate_oee_trend

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["Views"])


@router.get("/")
def dashboard_view(
    request: Request,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    machine_ids: Optional[str] = None,
    shift_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    if end_time is None:
        end_time = datetime.now()
    if start_time is None:
        start_time = end_time - timedelta(hours=24)

    parsed_ids: Optional[List[int]] = None
    if machine_ids:
        try:
            parsed_ids = [
                int(mid.strip()) for mid in machine_ids.split(",") if mid.strip()
            ]
        except ValueError:
            parsed_ids = None

    metrics = calculate_dashboard_oee(
        session=db,
        start_time=start_time,
        end_time=end_time,
        machine_ids=parsed_ids,
        shift_id=shift_id,
    )
    machines = list(
        db.scalars(
            select(Machine).where(Machine.is_active == True).order_by(Machine.name)
        ).all()
    )
    shifts = list(
        db.scalars(
            select(Shift).where(Shift.is_active == True).order_by(Shift.name)
        ).all()
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "metrics": metrics,
            "machines": machines,
            "shifts": shifts,
            "start_time": start_time,
            "end_time": end_time,
            "machine_ids": machine_ids,
            "shift_id": shift_id,
        },
    )


@router.get("/dashboard/table")
def dashboard_table_fragment(
    request: Request,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    machine_ids: Optional[str] = None,
    shift_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    if end_time is None:
        end_time = datetime.now()
    if start_time is None:
        start_time = end_time - timedelta(hours=24)

    parsed_ids: Optional[List[int]] = None
    if machine_ids:
        try:
            parsed_ids = [
                int(mid.strip()) for mid in machine_ids.split(",") if mid.strip()
            ]
        except ValueError:
            parsed_ids = None

    metrics = calculate_dashboard_oee(
        session=db,
        start_time=start_time,
        end_time=end_time,
        machine_ids=parsed_ids,
        shift_id=shift_id,
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "metrics": metrics,
            "start_time": start_time,
            "end_time": end_time,
            "shift_id": shift_id,
        },
    )


@router.get("/machines")
def machines_list_view(
    request: Request,
    db: Session = Depends(get_db),
):
    machines = list(db.scalars(select(Machine).order_by(Machine.name)).all())
    return templates.TemplateResponse(
        request,
        "machines/list.html",
        {
            "machines": machines,
        },
    )


@router.get("/machines/new")
def new_machine_form(
    request: Request,
):
    return templates.TemplateResponse(
        request,
        "machines/form.html",
        {
            "machine": None,
        },
    )


@router.get("/machines/{machine_id}/edit")
def edit_machine_form(
    machine_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found.",
        )
    return templates.TemplateResponse(
        request,
        "machines/form.html",
        {
            "machine": machine,
        },
    )


@router.post("/machines")
def create_machine_view(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    ideal_cycle_time_seconds: Optional[float] = Form(1.0),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
):
    machine = Machine(
        code=code,
        name=name,
        description=description,
        ideal_cycle_time_seconds=ideal_cycle_time_seconds,
        is_active=is_active,
    )
    db.add(machine)
    db.commit()
    db.refresh(machine)
    machines = list(db.scalars(select(Machine).order_by(Machine.name)).all())
    return templates.TemplateResponse(
        request,
        "machines/list.html",
        {
            "machines": machines,
            "machine": machine,
        },
    )


@router.put("/machines/{machine_id}")
@router.post("/machines/{machine_id}")
def update_machine_view(
    machine_id: int,
    request: Request,
    code: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    ideal_cycle_time_seconds: Optional[float] = Form(None),
    is_active: Optional[bool] = Form(None),
    db: Session = Depends(get_db),
):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found.",
        )

    if code is not None:
        machine.code = code
    if name is not None:
        machine.name = name
    if description is not None:
        machine.description = description
    if ideal_cycle_time_seconds is not None:
        machine.ideal_cycle_time_seconds = ideal_cycle_time_seconds
    if is_active is not None:
        machine.is_active = is_active

    db.commit()
    db.refresh(machine)
    machines = list(db.scalars(select(Machine).order_by(Machine.name)).all())
    return templates.TemplateResponse(
        request,
        "machines/list.html",
        {
            "machines": machines,
            "machine": machine,
        },
    )


@router.delete("/machines/{machine_id}")
def delete_machine_view(
    machine_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found.",
        )
    machine.is_active = False
    db.commit()
    machines = list(db.scalars(select(Machine).order_by(Machine.name)).all())
    return templates.TemplateResponse(
        request,
        "machines/list.html",
        {
            "machines": machines,
        },
    )


@router.get("/shifts")
def shifts_list_view(
    request: Request,
    db: Session = Depends(get_db),
):
    shifts = list(db.scalars(select(Shift).order_by(Shift.start_time)).all())
    return templates.TemplateResponse(
        request,
        "shifts/list.html",
        {
            "shifts": shifts,
        },
    )


@router.get("/shifts/new")
def new_shift_form(
    request: Request,
):
    return templates.TemplateResponse(
        request,
        "shifts/form.html",
        {
            "shift": None,
        },
    )


@router.get("/shifts/{shift_id}/edit")
def edit_shift_form(
    shift_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with id {shift_id} not found.",
        )
    return templates.TemplateResponse(
        request,
        "shifts/form.html",
        {
            "shift": shift,
        },
    )


@router.post("/shifts")
def create_shift_view(
    request: Request,
    name: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    planned_break_minutes: int = Form(0),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
):
    parsed_start = time.fromisoformat(start_time)
    parsed_end = time.fromisoformat(end_time)

    shift = Shift(
        name=name,
        start_time=parsed_start,
        end_time=parsed_end,
        planned_break_minutes=planned_break_minutes,
        is_active=is_active,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    shifts = list(db.scalars(select(Shift).order_by(Shift.start_time)).all())
    return templates.TemplateResponse(
        request,
        "shifts/list.html",
        {
            "shifts": shifts,
            "shift": shift,
        },
    )


@router.put("/shifts/{shift_id}")
@router.post("/shifts/{shift_id}")
def update_shift_view(
    shift_id: int,
    request: Request,
    name: Optional[str] = Form(None),
    start_time: Optional[str] = Form(None),
    end_time: Optional[str] = Form(None),
    planned_break_minutes: Optional[int] = Form(None),
    is_active: Optional[bool] = Form(None),
    db: Session = Depends(get_db),
):
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with id {shift_id} not found.",
        )

    if name is not None:
        shift.name = name
    if start_time is not None:
        shift.start_time = time.fromisoformat(start_time)
    if end_time is not None:
        shift.end_time = time.fromisoformat(end_time)
    if planned_break_minutes is not None:
        shift.planned_break_minutes = planned_break_minutes
    if is_active is not None:
        shift.is_active = is_active

    db.commit()
    db.refresh(shift)
    shifts = list(db.scalars(select(Shift).order_by(Shift.start_time)).all())
    return templates.TemplateResponse(
        request,
        "shifts/list.html",
        {
            "shifts": shifts,
            "shift": shift,
        },
    )


@router.delete("/shifts/{shift_id}")
def delete_shift_view(
    shift_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with id {shift_id} not found.",
        )
    shift.is_active = False
    db.commit()
    shifts = list(db.scalars(select(Shift).order_by(Shift.start_time)).all())
    return templates.TemplateResponse(
        request,
        "shifts/list.html",
        {
            "shifts": shifts,
        },
    )


@router.get("/downtime-events")
def downtime_events_view(
    request: Request,
    db: Session = Depends(get_db),
):
    open_events = list(
        db.scalars(
            select(DowntimeEvent)
            .options(
                joinedload(DowntimeEvent.reason), joinedload(DowntimeEvent.machine)
            )
            .where(DowntimeEvent.end_time.is_(None))
            .order_by(DowntimeEvent.start_time.desc())
        ).all()
    )
    recent_events = list(
        db.scalars(
            select(DowntimeEvent)
            .options(
                joinedload(DowntimeEvent.reason), joinedload(DowntimeEvent.machine)
            )
            .order_by(DowntimeEvent.start_time.desc())
            .limit(50)
        ).all()
    )
    machines = list(
        db.scalars(
            select(Machine).where(Machine.is_active == True).order_by(Machine.name)
        ).all()
    )
    reasons = list(
        db.scalars(
            select(DowntimeReason)
            .where(DowntimeReason.is_active == True)
            .order_by(DowntimeReason.name)
        ).all()
    )
    shifts = list(
        db.scalars(
            select(Shift).where(Shift.is_active == True).order_by(Shift.name)
        ).all()
    )

    return templates.TemplateResponse(
        request,
        "downtime_events.html",
        {
            "open_events": open_events,
            "events": recent_events,
            "machines": machines,
            "reasons": reasons,
            "shifts": shifts,
        },
    )


@router.post("/downtime-events/start")
def start_downtime_event_view(
    request: Request,
    machine_id: int = Form(...),
    reason_id: int = Form(...),
    shift_id: Optional[int] = Form(None),
    operator_name: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    start_time: Optional[datetime] = Form(None),
    db: Session = Depends(get_db),
):
    if not db.get(Machine, machine_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found.",
        )
    if not db.get(DowntimeReason, reason_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Downtime reason with id {reason_id} not found.",
        )

    event = DowntimeEvent(
        machine_id=machine_id,
        reason_id=reason_id,
        shift_id=shift_id,
        operator_name=operator_name,
        notes=notes,
        start_time=start_time or datetime.now(),
        end_time=None,
    )
    db.add(event)
    db.commit()

    open_events = list(
        db.scalars(
            select(DowntimeEvent)
            .options(
                joinedload(DowntimeEvent.reason), joinedload(DowntimeEvent.machine)
            )
            .where(DowntimeEvent.end_time.is_(None))
            .order_by(DowntimeEvent.start_time.desc())
        ).all()
    )
    recent_events = list(
        db.scalars(
            select(DowntimeEvent)
            .options(
                joinedload(DowntimeEvent.reason), joinedload(DowntimeEvent.machine)
            )
            .order_by(DowntimeEvent.start_time.desc())
            .limit(50)
        ).all()
    )
    machines = list(
        db.scalars(
            select(Machine).where(Machine.is_active == True).order_by(Machine.name)
        ).all()
    )
    reasons = list(
        db.scalars(
            select(DowntimeReason)
            .where(DowntimeReason.is_active == True)
            .order_by(DowntimeReason.name)
        ).all()
    )
    shifts = list(
        db.scalars(
            select(Shift).where(Shift.is_active == True).order_by(Shift.name)
        ).all()
    )

    return templates.TemplateResponse(
        request,
        "downtime_events.html",
        {
            "open_events": open_events,
            "events": recent_events,
            "machines": machines,
            "reasons": reasons,
            "shifts": shifts,
        },
    )


@router.post("/downtime-events/{event_id}/stop")
def stop_downtime_event_view(
    event_id: int,
    request: Request,
    end_time: Optional[datetime] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    event = db.get(DowntimeEvent, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Downtime event with id {event_id} not found.",
        )

    stop_time = end_time or datetime.now()
    if stop_time <= event.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be after start_time.",
        )

    event.end_time = stop_time
    if notes is not None:
        event.notes = notes

    db.commit()

    open_events = list(
        db.scalars(
            select(DowntimeEvent)
            .options(
                joinedload(DowntimeEvent.reason), joinedload(DowntimeEvent.machine)
            )
            .where(DowntimeEvent.end_time.is_(None))
            .order_by(DowntimeEvent.start_time.desc())
        ).all()
    )
    recent_events = list(
        db.scalars(
            select(DowntimeEvent)
            .options(
                joinedload(DowntimeEvent.reason), joinedload(DowntimeEvent.machine)
            )
            .order_by(DowntimeEvent.start_time.desc())
            .limit(50)
        ).all()
    )
    machines = list(
        db.scalars(
            select(Machine).where(Machine.is_active == True).order_by(Machine.name)
        ).all()
    )
    reasons = list(
        db.scalars(
            select(DowntimeReason)
            .where(DowntimeReason.is_active == True)
            .order_by(DowntimeReason.name)
        ).all()
    )
    shifts = list(
        db.scalars(
            select(Shift).where(Shift.is_active == True).order_by(Shift.name)
        ).all()
    )

    return templates.TemplateResponse(
        request,
        "downtime_events.html",
        {
            "open_events": open_events,
            "events": recent_events,
            "machines": machines,
            "reasons": reasons,
            "shifts": shifts,
        },
    )


@router.get("/production-runs")
def production_runs_view(
    request: Request,
    db: Session = Depends(get_db),
):
    runs = list(
        db.scalars(
            select(ProductionRun)
            .options(joinedload(ProductionRun.machine), joinedload(ProductionRun.shift))
            .order_by(ProductionRun.start_time.desc())
            .limit(50)
        ).all()
    )
    machines = list(
        db.scalars(
            select(Machine).where(Machine.is_active == True).order_by(Machine.name)
        ).all()
    )
    shifts = list(
        db.scalars(
            select(Shift).where(Shift.is_active == True).order_by(Shift.name)
        ).all()
    )

    return templates.TemplateResponse(
        request,
        "production_runs.html",
        {
            "runs": runs,
            "machines": machines,
            "shifts": shifts,
        },
    )


@router.post("/production-runs")
def create_production_run_view(
    request: Request,
    machine_id: int = Form(...),
    shift_id: Optional[int] = Form(None),
    product_code: Optional[str] = Form(None),
    product_name: Optional[str] = Form(None),
    start_time: Optional[datetime] = Form(None),
    end_time: Optional[datetime] = Form(None),
    target_units: int = Form(0),
    total_units: int = Form(0),
    scrap_units: int = Form(0),
    ideal_cycle_time_seconds: float = Form(1.0),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if not db.get(Machine, machine_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found.",
        )

    run_start = start_time or datetime.now()
    if end_time and end_time <= run_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be after start_time.",
        )

    run = ProductionRun(
        machine_id=machine_id,
        shift_id=shift_id,
        product_code=product_code,
        product_name=product_name,
        start_time=run_start,
        end_time=end_time,
        target_units=target_units,
        total_units=total_units,
        scrap_units=scrap_units,
        ideal_cycle_time_seconds=ideal_cycle_time_seconds,
        notes=notes,
    )
    db.add(run)
    db.commit()

    runs = list(
        db.scalars(
            select(ProductionRun)
            .options(joinedload(ProductionRun.machine), joinedload(ProductionRun.shift))
            .order_by(ProductionRun.start_time.desc())
            .limit(50)
        ).all()
    )
    machines = list(
        db.scalars(
            select(Machine).where(Machine.is_active == True).order_by(Machine.name)
        ).all()
    )
    shifts = list(
        db.scalars(
            select(Shift).where(Shift.is_active == True).order_by(Shift.name)
        ).all()
    )

    return templates.TemplateResponse(
        request,
        "production_runs.html",
        {
            "runs": runs,
            "machines": machines,
            "shifts": shifts,
        },
    )


@router.get("/reports")
def reports_view(
    request: Request,
    machine_id: Optional[int] = None,
    range: str = "7d",
    granularity: str = "daily",
    db: Session = Depends(get_db),
):
    machines = list(
        db.scalars(
            select(Machine).where(Machine.is_active == True).order_by(Machine.name)
        ).all()
    )

    selected_machine_id = machine_id
    if selected_machine_id is None and machines:
        selected_machine_id = machines[0].id

    days = 30 if range == "30d" else 7
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    trend_data = []
    selected_machine = None
    if selected_machine_id:
        selected_machine = db.get(Machine, selected_machine_id)
        trend_results = calculate_oee_trend(
            session=db,
            machine_id=selected_machine_id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
        )
        trend_data = [t.model_dump(mode="json") for t in trend_results]

    return templates.TemplateResponse(
        request,
        "reports.html",
        {
            "machines": machines,
            "selected_machine": selected_machine,
            "selected_machine_id": selected_machine_id,
            "range": range,
            "granularity": granularity,
            "trend_data": trend_data,
        },
    )


@router.get("/reports/chart")
def reports_chart_fragment(
    request: Request,
    machine_id: Optional[int] = None,
    range: str = "7d",
    granularity: str = "daily",
    db: Session = Depends(get_db),
):
    machines = list(
        db.scalars(
            select(Machine).where(Machine.is_active == True).order_by(Machine.name)
        ).all()
    )

    selected_machine_id = machine_id
    if selected_machine_id is None and machines:
        selected_machine_id = machines[0].id

    days = 30 if range == "30d" else 7
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    trend_data = []
    selected_machine = None
    if selected_machine_id:
        selected_machine = db.get(Machine, selected_machine_id)
        trend_results = calculate_oee_trend(
            session=db,
            machine_id=selected_machine_id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
        )
        trend_data = [t.model_dump(mode="json") for t in trend_results]

    return templates.TemplateResponse(
        request,
        "reports.html",
        {
            "machines": machines,
            "selected_machine": selected_machine,
            "selected_machine_id": selected_machine_id,
            "range": range,
            "granularity": granularity,
            "trend_data": trend_data,
        },
    )
