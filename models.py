import enum
from datetime import datetime, time
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DowntimeCategory(str, enum.Enum):
    BREAKDOWN = "breakdown"
    CHANGEOVER = "changeover"
    PLANNED_MAINTENANCE = "planned_maintenance"
    BREAK = "break"
    OTHER = "other"


# Represents a manufacturing line or individual machine tracked for OEE and downtime.
class Machine(Base, TimestampMixin):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ideal_cycle_time_seconds: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=1.0
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    downtime_events: Mapped[List["DowntimeEvent"]] = relationship(
        "DowntimeEvent", back_populates="machine", cascade="all, delete-orphan"
    )
    production_runs: Mapped[List["ProductionRun"]] = relationship(
        "ProductionRun", back_populates="machine", cascade="all, delete-orphan"
    )


# Defines workshop operational shift schedules and planned working hours.
class Shift(Base, TimestampMixin):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    planned_break_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    downtime_events: Mapped[List["DowntimeEvent"]] = relationship(
        "DowntimeEvent", back_populates="shift"
    )
    production_runs: Mapped[List["ProductionRun"]] = relationship(
        "ProductionRun", back_populates="shift"
    )


# Categorizes downtime events with customizable classifications and planned/unplanned indicators.
class DowntimeReason(Base, TimestampMixin):
    __tablename__ = "downtime_reasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[DowntimeCategory] = mapped_column(
        Enum(DowntimeCategory, native_enum=False),
        default=DowntimeCategory.OTHER,
        nullable=False,
        index=True,
    )
    is_planned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    color_code: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    downtime_events: Mapped[List["DowntimeEvent"]] = relationship(
        "DowntimeEvent", back_populates="reason"
    )


# Logs start/stop downtime and changeover occurrences per machine for Availability calculations.
class DowntimeEvent(Base, TimestampMixin):
    __tablename__ = "downtime_events"
    __table_args__ = (
        Index("ix_downtime_events_machine_start", "machine_id", "start_time"),
        Index("ix_downtime_events_shift_start", "shift_id", "start_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("downtime_reasons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    shift_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    operator_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    machine: Mapped["Machine"] = relationship("Machine", back_populates="downtime_events")
    reason: Mapped["DowntimeReason"] = relationship("DowntimeReason", back_populates="downtime_events")
    shift: Mapped[Optional["Shift"]] = relationship("Shift", back_populates="downtime_events")


# Records unit counts, defects, and cycle times per machine/shift for Performance and Quality calculations.
class ProductionRun(Base, TimestampMixin):
    __tablename__ = "production_runs"
    __table_args__ = (
        Index("ix_production_runs_machine_start", "machine_id", "start_time"),
        Index("ix_production_runs_shift_start", "shift_id", "start_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shift_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    product_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    target_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scrap_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ideal_cycle_time_seconds: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    machine: Mapped["Machine"] = relationship("Machine", back_populates="production_runs")
    shift: Mapped[Optional["Shift"]] = relationship("Shift", back_populates="production_runs")
