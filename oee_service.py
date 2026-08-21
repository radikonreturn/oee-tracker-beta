from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, joinedload

from models import DowntimeEvent, Machine, ProductionRun


class OEEMetrics(BaseModel):
    machine_id: int
    machine_name: Optional[str] = None
    shift_id: Optional[int] = None
    start_time: datetime
    end_time: datetime

    # Time metrics in seconds
    total_window_seconds: float = Field(..., description="Total elapsed seconds in the evaluation window")
    planned_downtime_seconds: float = Field(..., description="Planned downtime (breaks, maintenance) in seconds")
    unplanned_downtime_seconds: float = Field(..., description="Unplanned downtime (breakdowns, changeovers) in seconds")
    planned_production_time_seconds: float = Field(..., description="Total window time minus planned downtime")
    run_time_seconds: float = Field(..., description="Actual operating time (Planned Production Time - Unplanned Downtime)")

    # Production counts
    target_units: int = Field(0, description="Total target/planned units")
    total_units: int = Field(0, description="Total units produced (good + scrap)")
    good_units: int = Field(0, description="Good units produced (total - scrap)")
    scrap_units: int = Field(0, description="Defective or scrap units")

    # Core OEE components (range 0.0 - 1.0, though performance may exceed 1.0 if running faster than ideal)
    availability: float = Field(..., description="Availability ratio (Run Time / Planned Production Time)")
    performance: float = Field(..., description="Performance ratio ((Total Units * Ideal Cycle Time) / Run Time)")
    quality: float = Field(..., description="Quality ratio (Good Units / Total Units)")
    oee: float = Field(..., description="Overall Equipment Effectiveness (Availability * Performance * Quality)")

    # Breakdown count metadata
    downtime_event_count: int = Field(0, description="Number of recorded downtime events in window")
    production_run_count: int = Field(0, description="Number of recorded production runs in window")


class OEETrendBucket(BaseModel):
    label: str
    start_time: datetime
    end_time: datetime
    availability: float
    performance: float
    quality: float
    oee: float
    total_units: int
    good_units: int
    scrap_units: int
    run_time_seconds: float
    unplanned_downtime_seconds: float


# Computes the clamped overlap duration in seconds between an event and a time window.
def calculate_overlap_seconds(
    event_start: datetime,
    event_end: Optional[datetime],
    window_start: datetime,
    window_end: datetime,
) -> float:
    effective_end = event_end if event_end is not None else window_end
    clipped_start = max(event_start, window_start)
    clipped_end = min(effective_end, window_end)
    overlap = (clipped_end - clipped_start).total_seconds()
    return max(0.0, overlap)


# Computes complete Availability, Performance, Quality, and OEE metrics with intermediate breakdown values for a specific machine.
def calculate_machine_oee(
    session: Session,
    machine_id: int,
    start_time: datetime,
    end_time: datetime,
    shift_id: Optional[int] = None,
) -> OEEMetrics:
    if end_time <= start_time:
        raise ValueError("end_time must be strictly greater than start_time")

    machine = session.get(Machine, machine_id)
    machine_name = machine.name if machine else None

    total_window_seconds = max(0.0, (end_time - start_time).total_seconds())

    # Query downtime events overlapping the window
    downtime_query = (
        select(DowntimeEvent)
        .options(joinedload(DowntimeEvent.reason))
        .where(
            DowntimeEvent.machine_id == machine_id,
            DowntimeEvent.start_time < end_time,
            or_(DowntimeEvent.end_time.is_(None), DowntimeEvent.end_time > start_time),
        )
    )
    if shift_id is not None:
        downtime_query = downtime_query.where(DowntimeEvent.shift_id == shift_id)

    downtime_events = session.scalars(downtime_query).all()

    planned_downtime_seconds = 0.0
    unplanned_downtime_seconds = 0.0

    for event in downtime_events:
        duration = calculate_overlap_seconds(event.start_time, event.end_time, start_time, end_time)
        if event.reason and event.reason.is_planned:
            planned_downtime_seconds += duration
        else:
            unplanned_downtime_seconds += duration

    # Query production runs overlapping the window
    production_query = select(ProductionRun).where(
        ProductionRun.machine_id == machine_id,
        ProductionRun.start_time < end_time,
        or_(ProductionRun.end_time.is_(None), ProductionRun.end_time > start_time),
    )
    if shift_id is not None:
        production_query = production_query.where(ProductionRun.shift_id == shift_id)

    production_runs = session.scalars(production_query).all()

    total_target_units = 0
    total_produced_units = 0
    total_scrap_units = 0
    standard_operating_time_seconds = 0.0

    for run in production_runs:
        total_target_units += max(0, run.target_units)
        total_produced_units += max(0, run.total_units)
        total_scrap_units += max(0, run.scrap_units)
        cycle_time = run.ideal_cycle_time_seconds if run.ideal_cycle_time_seconds > 0 else 1.0
        standard_operating_time_seconds += max(0, run.total_units) * cycle_time

    good_units = max(0, total_produced_units - total_scrap_units)

    # Time calculations
    planned_production_time_seconds = max(0.0, total_window_seconds - planned_downtime_seconds)
    run_time_seconds = max(0.0, planned_production_time_seconds - unplanned_downtime_seconds)

    # Metric calculations with zero-division guards
    availability = (
        (run_time_seconds / planned_production_time_seconds)
        if planned_production_time_seconds > 0.0
        else 0.0
    )
    availability = min(max(0.0, availability), 1.0)

    performance = (
        (standard_operating_time_seconds / run_time_seconds)
        if run_time_seconds > 0.0
        else 0.0
    )
    performance = max(0.0, performance)

    quality = (
        (good_units / total_produced_units)
        if total_produced_units > 0
        else 0.0
    )
    quality = min(max(0.0, quality), 1.0)

    oee = availability * performance * quality

    return OEEMetrics(
        machine_id=machine_id,
        machine_name=machine_name,
        shift_id=shift_id,
        start_time=start_time,
        end_time=end_time,
        total_window_seconds=round(total_window_seconds, 2),
        planned_downtime_seconds=round(planned_downtime_seconds, 2),
        unplanned_downtime_seconds=round(unplanned_downtime_seconds, 2),
        planned_production_time_seconds=round(planned_production_time_seconds, 2),
        run_time_seconds=round(run_time_seconds, 2),
        target_units=total_target_units,
        total_units=total_produced_units,
        good_units=good_units,
        scrap_units=total_scrap_units,
        availability=round(availability, 4),
        performance=round(performance, 4),
        quality=round(quality, 4),
        oee=round(oee, 4),
        downtime_event_count=len(downtime_events),
        production_run_count=len(production_runs),
    )


# Computes OEE breakdown metrics for multiple machines over a date range for fleet and dashboard views.
def calculate_dashboard_oee(
    session: Session,
    start_time: datetime,
    end_time: datetime,
    machine_ids: Optional[List[int]] = None,
    shift_id: Optional[int] = None,
) -> List[OEEMetrics]:
    if machine_ids is None:
        stmt = select(Machine.id).where(Machine.is_active == True).order_by(Machine.name)
        target_machine_ids = list(session.scalars(stmt).all())
    else:
        target_machine_ids = machine_ids

    results: List[OEEMetrics] = []
    for m_id in target_machine_ids:
        metrics = calculate_machine_oee(
            session=session,
            machine_id=m_id,
            start_time=start_time,
            end_time=end_time,
            shift_id=shift_id,
        )
        results.append(metrics)

    return results


# Computes bucketed historical OEE metrics over a date range for trends and reporting.
def calculate_oee_trend(
    session: Session,
    machine_id: int,
    start_date: datetime,
    end_date: datetime,
    granularity: str = "daily",
    shift_id: Optional[int] = None,
) -> List[OEETrendBucket]:
    if end_date <= start_date:
        raise ValueError("end_date must be strictly greater than start_date")

    buckets: List[OEETrendBucket] = []
    delta = timedelta(days=7 if granularity == "weekly" else 1)

    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + delta, end_date)
        metrics = calculate_machine_oee(
            session=session,
            machine_id=machine_id,
            start_time=current_start,
            end_time=current_end,
            shift_id=shift_id,
        )

        label = (
            f"{current_start.strftime('%b %d')} - {current_end.strftime('%b %d')}"
            if granularity == "weekly"
            else current_start.strftime("%b %d")
        )

        buckets.append(
            OEETrendBucket(
                label=label,
                start_time=current_start,
                end_time=current_end,
                availability=metrics.availability,
                performance=metrics.performance,
                quality=metrics.quality,
                oee=metrics.oee,
                total_units=metrics.total_units,
                good_units=metrics.good_units,
                scrap_units=metrics.scrap_units,
                run_time_seconds=metrics.run_time_seconds,
                unplanned_downtime_seconds=metrics.unplanned_downtime_seconds,
            )
        )
        current_start = current_end

    return buckets
