from datetime import datetime, time
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models import Base, Machine, Shift, DowntimeReason, DowntimeCategory, DowntimeEvent, ProductionRun
from oee_service import calculate_machine_oee, calculate_dashboard_oee


def main():
    print("=" * 70)
    print("  OEETracker - SQLite Database & OEE Engine Demonstration")
    print("=" * 70)

    # 1. Initialize in-memory SQLite engine
    engine = create_engine("sqlite:///oee_tracker.db", echo=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("-> SQLite database schema created successfully.\n")

    with Session(engine) as session:
        # 2. Seed Machines
        cnc_1 = Machine(
            code="CNC-01",
            name="5-Axis CNC Milling Station #1",
            description="Main production CNC milling unit",
            ideal_cycle_time_seconds=30.0,
            is_active=True,
        )
        cnc_2 = Machine(
            code="CNC-02",
            name="Lathe Turning Center #2",
            description="Secondary turning line",
            ideal_cycle_time_seconds=45.0,
            is_active=True,
        )
        session.add_all([cnc_1, cnc_2])
        session.flush()

        # 3. Seed Shift (8 hour shift: 08:00 to 16:00, 28,800 seconds total)
        morning_shift = Shift(
            name="Morning Shift",
            start_time=time(8, 0),
            end_time=time(16, 0),
            planned_break_minutes=60,
            is_active=True,
        )
        session.add(morning_shift)
        session.flush()

        # 4. Seed Downtime Reasons
        reason_break = DowntimeReason(
            name="Scheduled Lunch & Tea Break",
            category=DowntimeCategory.BREAK,
            is_planned=True,
            color_code="#3B82F6",
        )
        reason_maint = DowntimeReason(
            name="Planned Weekly PM",
            category=DowntimeCategory.PLANNED_MAINTENANCE,
            is_planned=True,
            color_code="#10B981",
        )
        reason_breakdown = DowntimeReason(
            name="Hydraulic Pressure Loss",
            category=DowntimeCategory.BREAKDOWN,
            is_planned=False,
            color_code="#EF4444",
        )
        reason_changeover = DowntimeReason(
            name="Tooling & Fixture Changeover",
            category=DowntimeCategory.CHANGEOVER,
            is_planned=False,
            color_code="#F59E0B",
        )
        session.add_all([reason_break, reason_maint, reason_breakdown, reason_changeover])
        session.flush()

        # 5. Seed Downtime Events for CNC-01 (Total window: 8:00 - 16:00 = 8h = 28,800s)
        # Planned: 45 min Lunch (2,700s)
        # Unplanned: 30 min Breakdown (1,800s) + 20 min Changeover (1,200s) = 3,000s
        # Planned Prod Time = 28,800 - 2,700 = 26,100s
        # Run Time = 26,100 - 3,000 = 23,100s
        # Availability = 23,100 / 26,100 = ~88.51%
        event_1 = DowntimeEvent(
            machine_id=cnc_1.id,
            reason_id=reason_break.id,
            shift_id=morning_shift.id,
            start_time=datetime(2026, 8, 20, 12, 0, 0),
            end_time=datetime(2026, 8, 20, 12, 45, 0),
            operator_name="John Doe",
            notes="Lunch break",
        )
        event_2 = DowntimeEvent(
            machine_id=cnc_1.id,
            reason_id=reason_breakdown.id,
            shift_id=morning_shift.id,
            start_time=datetime(2026, 8, 20, 9, 30, 0),
            end_time=datetime(2026, 8, 20, 10, 0, 0),
            operator_name="John Doe",
            notes="Pump valve replacement",
        )
        event_3 = DowntimeEvent(
            machine_id=cnc_1.id,
            reason_id=reason_changeover.id,
            shift_id=morning_shift.id,
            start_time=datetime(2026, 8, 20, 14, 0, 0),
            end_time=datetime(2026, 8, 20, 14, 20, 0),
            operator_name="John Doe",
            notes="Swapped cutter heads for Batch B",
        )
        session.add_all([event_1, event_2, event_3])

        # 6. Seed Production Runs for CNC-01
        # Target: 750 units. Produced: 700 units. Scrap: 20 units. Good: 680 units.
        # Ideal Cycle Time: 30.0 sec/unit
        # Standard Operating Time = 700 * 30.0 = 21,000s
        # Performance = 21,000 / 23,100 = ~90.91%
        # Quality = 680 / 700 = ~97.14%
        # Expected OEE = 0.8851 * 0.9091 * 0.9714 = ~78.16%
        run_1 = ProductionRun(
            machine_id=cnc_1.id,
            shift_id=morning_shift.id,
            product_code="PART-A100",
            product_name="Aluminum Gear Housing",
            start_time=datetime(2026, 8, 20, 8, 0, 0),
            end_time=datetime(2026, 8, 20, 16, 0, 0),
            target_units=750,
            total_units=700,
            scrap_units=20,
            ideal_cycle_time_seconds=30.0,
            notes="Regular production run",
        )
        session.add(run_1)

        # 7. Seed Production Runs for CNC-02
        run_2 = ProductionRun(
            machine_id=cnc_2.id,
            shift_id=morning_shift.id,
            product_code="SHAFT-B200",
            product_name="Stainless Steel Shaft",
            start_time=datetime(2026, 8, 20, 8, 0, 0),
            end_time=datetime(2026, 8, 20, 16, 0, 0),
            target_units=500,
            total_units=480,
            scrap_units=10,
            ideal_cycle_time_seconds=45.0,
            notes="Smooth run without interruptions",
        )
        session.add(run_2)
        session.commit()
        print("-> Sample production & downtime seed data committed successfully.\n")

        # 8. Compute OEE for CNC-01
        window_start = datetime(2026, 8, 20, 8, 0, 0)
        window_end = datetime(2026, 8, 20, 16, 0, 0)

        metrics_cnc1 = calculate_machine_oee(
            session=session,
            machine_id=cnc_1.id,
            start_time=window_start,
            end_time=window_end,
            shift_id=morning_shift.id,
        )

        print("-" * 70)
        print(f"  SINGLE MACHINE OEE BREAKDOWN: {metrics_cnc1.machine_name} ({cnc_1.code})")
        print("-" * 70)
        print(f"  Evaluation Window : {metrics_cnc1.start_time} to {metrics_cnc1.end_time} ({metrics_cnc1.total_window_seconds/3600:.1f} hrs)")
        print(f"  Planned Downtime  : {metrics_cnc1.planned_downtime_seconds / 60:.1f} mins ({metrics_cnc1.planned_downtime_seconds:.0f}s)")
        print(f"  Unplanned Downtime: {metrics_cnc1.unplanned_downtime_seconds / 60:.1f} mins ({metrics_cnc1.unplanned_downtime_seconds:.0f}s)")
        print(f"  Planned Prod Time : {metrics_cnc1.planned_production_time_seconds / 60:.1f} mins ({metrics_cnc1.planned_production_time_seconds:.0f}s)")
        print(f"  Operating Run Time: {metrics_cnc1.run_time_seconds / 60:.1f} mins ({metrics_cnc1.run_time_seconds:.0f}s)")
        print(f"  Production Counts : Total = {metrics_cnc1.total_units} | Good = {metrics_cnc1.good_units} | Scrap = {metrics_cnc1.scrap_units} (Target: {metrics_cnc1.target_units})")
        print("  " + "-" * 66)
        print(f"  Availability Rate : {metrics_cnc1.availability * 100:.2f}%")
        print(f"  Performance Rate  : {metrics_cnc1.performance * 100:.2f}%")
        print(f"  Quality Rate      : {metrics_cnc1.quality * 100:.2f}%")
        print(f"  OVERALL OEE       : {metrics_cnc1.oee * 100:.2f}%")
        print("-" * 70 + "\n")

        # 9. Compute Dashboard OEE across all machines
        dashboard = calculate_dashboard_oee(
            session=session,
            start_time=window_start,
            end_time=window_end,
            shift_id=morning_shift.id,
        )

        print("-" * 70)
        print("  FLEET / DASHBOARD VIEW (ALL ACTIVE MACHINES)")
        print("-" * 70)
        for m in dashboard:
            print(f"  • Machine #{m.machine_id} [{m.machine_name}]:")
            print(f"    - Availability: {m.availability * 100:.2f}% | Performance: {m.performance * 100:.2f}% | Quality: {m.quality * 100:.2f}%")
            print(f"    - Overall OEE : {m.oee * 100:.2f}%\n")
        print("=" * 70)


if __name__ == "__main__":
    main()
