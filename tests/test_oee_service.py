from datetime import datetime, time
import pytest
from sqlalchemy.orm import Session

from models import DowntimeCategory
from oee_service import (
    calculate_dashboard_oee,
    calculate_machine_oee,
    calculate_oee_trend,
)


def test_clean_production_case(
    db_session: Session,
    machine_factory,
    production_run_factory,
):
    # 8-hour window = 28,800 seconds
    window_start = datetime(2026, 8, 20, 8, 0, 0)
    window_end = datetime(2026, 8, 20, 16, 0, 0)

    machine = machine_factory(ideal_cycle_time_seconds=28.8)
    production_run_factory(
        machine_id=machine.id,
        start_time=window_start,
        end_time=window_end,
        target_units=1000,
        total_units=1000,
        scrap_units=50,
        ideal_cycle_time_seconds=28.8,
    )

    metrics = calculate_machine_oee(
        session=db_session,
        machine_id=machine.id,
        start_time=window_start,
        end_time=window_end,
    )

    # Planned Prod Time = 28,800s, Run Time = 28,800s -> Availability = 1.0
    assert metrics.availability == pytest.approx(1.0)
    # Operating time = 1000 * 28.8 = 28,800s -> Performance = 28,800 / 28,800 = 1.0
    assert metrics.performance == pytest.approx(1.0)
    # Good = 950, Total = 1000 -> Quality = 950 / 1000 = 0.95
    assert metrics.quality == pytest.approx(0.95)
    # OEE = 1.0 * 1.0 * 0.95 = 0.95
    assert metrics.oee == pytest.approx(0.95)
    assert metrics.good_units == 950
    assert metrics.scrap_units == 50


def test_unplanned_downtime_reduces_availability(
    db_session: Session,
    machine_factory,
    downtime_reason_factory,
    downtime_event_factory,
):
    window_start = datetime(2026, 8, 20, 8, 0, 0)
    window_end = datetime(2026, 8, 20, 16, 0, 0)  # 28,800s

    machine = machine_factory()
    breakdown_reason = downtime_reason_factory(
        name="Motor Overheat",
        category=DowntimeCategory.BREAKDOWN,
        is_planned=False,
    )

    # 2 hours (7,200s) unplanned breakdown
    downtime_event_factory(
        machine_id=machine.id,
        reason_id=breakdown_reason.id,
        start_time=datetime(2026, 8, 20, 10, 0, 0),
        end_time=datetime(2026, 8, 20, 12, 0, 0),
    )

    metrics = calculate_machine_oee(
        session=db_session,
        machine_id=machine.id,
        start_time=window_start,
        end_time=window_end,
    )

    # Planned Prod Time = 28,800s, Run Time = 28,800 - 7,200 = 21,600s
    # Availability = 21,600 / 28,800 = 0.75
    assert metrics.unplanned_downtime_seconds == pytest.approx(7200.0)
    assert metrics.run_time_seconds == pytest.approx(21600.0)
    assert metrics.availability == pytest.approx(0.75)


def test_planned_downtime_does_not_reduce_availability(
    db_session: Session,
    machine_factory,
    downtime_reason_factory,
    downtime_event_factory,
):
    window_start = datetime(2026, 8, 20, 8, 0, 0)
    window_end = datetime(2026, 8, 20, 16, 0, 0)  # 28,800s

    machine = machine_factory()
    planned_reason = downtime_reason_factory(
        name="Planned Maintenance",
        category=DowntimeCategory.PLANNED_MAINTENANCE,
        is_planned=True,
    )

    # 1 hour (3,600s) planned maintenance
    downtime_event_factory(
        machine_id=machine.id,
        reason_id=planned_reason.id,
        start_time=datetime(2026, 8, 20, 12, 0, 0),
        end_time=datetime(2026, 8, 20, 13, 0, 0),
    )

    metrics = calculate_machine_oee(
        session=db_session,
        machine_id=machine.id,
        start_time=window_start,
        end_time=window_end,
    )

    # Planned Prod Time = 28,800 - 3,600 = 25,200s
    # Unplanned Downtime = 0s -> Run Time = 25,200s
    # Availability = 25,200 / 25,200 = 1.0
    assert metrics.planned_downtime_seconds == pytest.approx(3600.0)
    assert metrics.unplanned_downtime_seconds == pytest.approx(0.0)
    assert metrics.planned_production_time_seconds == pytest.approx(25200.0)
    assert metrics.run_time_seconds == pytest.approx(25200.0)
    assert metrics.availability == pytest.approx(1.0)


def test_scrap_units_reduce_quality(
    db_session: Session,
    machine_factory,
    production_run_factory,
):
    window_start = datetime(2026, 8, 20, 8, 0, 0)
    window_end = datetime(2026, 8, 20, 16, 0, 0)

    machine = machine_factory()
    production_run_factory(
        machine_id=machine.id,
        start_time=window_start,
        end_time=window_end,
        total_units=1000,
        scrap_units=200,
    )

    metrics = calculate_machine_oee(
        session=db_session,
        machine_id=machine.id,
        start_time=window_start,
        end_time=window_end,
    )

    assert metrics.total_units == 1000
    assert metrics.scrap_units == 200
    assert metrics.good_units == 800
    assert metrics.quality == pytest.approx(0.80)


def test_zero_planned_production_time_handles_division_by_zero(
    db_session: Session,
    machine_factory,
    downtime_reason_factory,
    downtime_event_factory,
):
    window_start = datetime(2026, 8, 20, 8, 0, 0)
    window_end = datetime(2026, 8, 20, 16, 0, 0)  # 28,800s

    machine = machine_factory()
    planned_reason = downtime_reason_factory(
        name="Full Day Maintenance",
        category=DowntimeCategory.PLANNED_MAINTENANCE,
        is_planned=True,
    )

    # 8 hours planned stop covering full window
    downtime_event_factory(
        machine_id=machine.id,
        reason_id=planned_reason.id,
        start_time=window_start,
        end_time=window_end,
    )

    metrics = calculate_machine_oee(
        session=db_session,
        machine_id=machine.id,
        start_time=window_start,
        end_time=window_end,
    )

    assert metrics.planned_production_time_seconds == pytest.approx(0.0)
    assert metrics.run_time_seconds == pytest.approx(0.0)
    assert metrics.availability == 0.0
    assert metrics.oee == 0.0


def test_zero_total_units_handles_division_by_zero(
    db_session: Session,
    machine_factory,
):
    window_start = datetime(2026, 8, 20, 8, 0, 0)
    window_end = datetime(2026, 8, 20, 16, 0, 0)

    machine = machine_factory()
    metrics = calculate_machine_oee(
        session=db_session,
        machine_id=machine.id,
        start_time=window_start,
        end_time=window_end,
    )

    assert metrics.total_units == 0
    assert metrics.good_units == 0
    assert metrics.quality == 0.0
    assert metrics.performance == 0.0
    assert metrics.oee == 0.0


def test_in_progress_downtime_event_clips_to_window(
    db_session: Session,
    machine_factory,
    downtime_reason_factory,
    downtime_event_factory,
):
    window_start = datetime(2026, 8, 20, 8, 0, 0)
    window_end = datetime(2026, 8, 20, 16, 0, 0)

    machine = machine_factory()
    reason = downtime_reason_factory(is_planned=False)

    # Started at 14:00 (2h before window_end), end_time is None (in-progress)
    downtime_event_factory(
        machine_id=machine.id,
        reason_id=reason.id,
        start_time=datetime(2026, 8, 20, 14, 0, 0),
        end_time=None,
    )

    metrics = calculate_machine_oee(
        session=db_session,
        machine_id=machine.id,
        start_time=window_start,
        end_time=window_end,
    )

    # Overlap should be clipped to window_end (14:00 to 16:00 = 7,200s)
    assert metrics.unplanned_downtime_seconds == pytest.approx(7200.0)


def test_performance_can_exceed_one_when_running_faster_than_ideal(
    db_session: Session,
    machine_factory,
    production_run_factory,
):
    window_start = datetime(2026, 8, 20, 8, 0, 0)
    window_end = datetime(2026, 8, 20, 16, 0, 0)  # 28,800s

    machine = machine_factory(ideal_cycle_time_seconds=30.0)
    # Produced 1200 units in 28,800s (ideal time = 1200 * 30 = 36,000s)
    production_run_factory(
        machine_id=machine.id,
        start_time=window_start,
        end_time=window_end,
        total_units=1200,
        scrap_units=0,
        ideal_cycle_time_seconds=30.0,
    )

    metrics = calculate_machine_oee(
        session=db_session,
        machine_id=machine.id,
        start_time=window_start,
        end_time=window_end,
    )

    # Performance = 36,000 / 28,800 = 1.25
    assert metrics.performance == pytest.approx(1.25)
    assert metrics.oee == pytest.approx(1.25)


def test_calculate_dashboard_oee_filtering(
    db_session: Session,
    machine_factory,
):
    window_start = datetime(2026, 8, 20, 8, 0, 0)
    window_end = datetime(2026, 8, 20, 16, 0, 0)

    m1 = machine_factory(code="CNC-01", is_active=True)
    m2 = machine_factory(code="CNC-02", is_active=True)
    m3 = machine_factory(code="CNC-03", is_active=False)

    all_dashboard = calculate_dashboard_oee(
        session=db_session,
        start_time=window_start,
        end_time=window_end,
    )
    # Should only return active machines (m1, m2)
    assert len(all_dashboard) == 2
    assert {m.machine_id for m in all_dashboard} == {m1.id, m2.id}

    filtered_dashboard = calculate_dashboard_oee(
        session=db_session,
        start_time=window_start,
        end_time=window_end,
        machine_ids=[m1.id],
    )
    assert len(filtered_dashboard) == 1
    assert filtered_dashboard[0].machine_id == m1.id


def test_calculate_oee_trend_buckets_alignment(
    db_session: Session,
    machine_factory,
):
    machine = machine_factory()
    start_date = datetime(2026, 8, 1, 0, 0, 0)
    end_date = datetime(2026, 8, 8, 0, 0, 0)  # Exactly 7 days

    daily_buckets = calculate_oee_trend(
        session=db_session,
        machine_id=machine.id,
        start_date=start_date,
        end_date=end_date,
        granularity="daily",
    )

    assert len(daily_buckets) == 7
    # Assert continuous boundary alignment without gaps or overlaps
    for i in range(len(daily_buckets) - 1):
        assert daily_buckets[i].end_time == daily_buckets[i + 1].start_time
    assert daily_buckets[0].start_time == start_date
    assert daily_buckets[-1].end_time == end_date
