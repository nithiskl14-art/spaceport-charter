from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Ship(BaseModel):
    id: int
    name: str


class BookingCreate(BaseModel):
    shipId: int
    pilotName: str = Field(min_length=1, max_length=100)
    startTime: datetime
    endTime: datetime

    @field_validator("pilotName")
    @classmethod
    def clean_pilot_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Pilot name is required")
        return value

    @field_validator("startTime", "endTime")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A timezone offset is required")
        return value


class Booking(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    shipId: int
    shipName: str
    pilotName: str
    startTime: datetime
    endTime: datetime


class BookingSummary(BaseModel):
    totalRecords: int
    latestBookingDate: date | None
    todayCount: int


class UnavailablePeriod(BaseModel):
    startTime: datetime
    endTime: datetime


class UnavailableResponse(BaseModel):
    shipId: int
    date: date
    timezone: str
    operatingStart: datetime
    operatingEnd: datetime
    refuelBufferMinutes: int
    unavailable: list[UnavailablePeriod]
