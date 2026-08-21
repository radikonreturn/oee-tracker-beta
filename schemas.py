from datetime import datetime, time
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from models import DowntimeCategory


# Machine Schemas
class MachineBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    ideal_cycle_time_seconds: Optional[float] = Field(1.0, gt=0)
    is_active: bool = True


class MachineCreate(MachineBase):
    pass


class MachineUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    ideal_cycle_time_seconds: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None


class MachineRead(MachineBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# Shift Schemas
class ShiftBase(BaseModel):
    name: str = Field(..., max_length=100)
    start_time: time
    end_time: time
    planned_break_minutes: int = Field(0, ge=0)
    is_active: bool = True


class ShiftCreate(ShiftBase):
    pass


class ShiftUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    planned_break_minutes: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ShiftRead(ShiftBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# DowntimeReason Schemas
class DowntimeReasonBase(BaseModel):
    name: str = Field(..., max_length=100)
    category: DowntimeCategory = DowntimeCategory.OTHER
    is_planned: bool = False
    color_code: Optional[str] = Field(None, max_length=7)
    is_active: bool = True


class DowntimeReasonCreate(DowntimeReasonBase):
    pass


class DowntimeReasonUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    category: Optional[DowntimeCategory] = None
    is_planned: Optional[bool] = None
    color_code: Optional[str] = Field(None, max_length=7)
    is_active: Optional[bool] = None


class DowntimeReasonRead(DowntimeReasonBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# DowntimeEvent Schemas
class DowntimeEventBase(BaseModel):
    machine_id: int
    reason_id: int
    shift_id: Optional[int] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    operator_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class DowntimeEventCreate(DowntimeEventBase):
    pass


class DowntimeEventUpdate(BaseModel):
    machine_id: Optional[int] = None
    reason_id: Optional[int] = None
    shift_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    operator_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class DowntimeEventRead(DowntimeEventBase):
    id: int
    created_at: datetime
    updated_at: datetime
    reason: Optional[DowntimeReasonRead] = None
    model_config = ConfigDict(from_attributes=True)


# ProductionRun Schemas
class ProductionRunBase(BaseModel):
    machine_id: int
    shift_id: Optional[int] = None
    product_code: Optional[str] = Field(None, max_length=100)
    product_name: Optional[str] = Field(None, max_length=150)
    start_time: datetime
    end_time: Optional[datetime] = None
    target_units: int = Field(0, ge=0)
    total_units: int = Field(0, ge=0)
    scrap_units: int = Field(0, ge=0)
    ideal_cycle_time_seconds: float = Field(1.0, gt=0)
    notes: Optional[str] = None


class ProductionRunCreate(ProductionRunBase):
    pass


class ProductionRunUpdate(BaseModel):
    machine_id: Optional[int] = None
    shift_id: Optional[int] = None
    product_code: Optional[str] = Field(None, max_length=100)
    product_name: Optional[str] = Field(None, max_length=150)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    target_units: Optional[int] = Field(None, ge=0)
    total_units: Optional[int] = Field(None, ge=0)
    scrap_units: Optional[int] = Field(None, ge=0)
    ideal_cycle_time_seconds: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = None


class ProductionRunRead(ProductionRunBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
