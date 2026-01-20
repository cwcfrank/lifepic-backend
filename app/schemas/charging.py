"""
Pydantic schemas for charging station API.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


# ============ Response Schemas ============

class ChargingStationBase(BaseModel):
    """Base charging station schema."""
    station_id: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    operator_name: Optional[str] = None
    phone: Optional[str] = None
    is_24h: Optional[bool] = None
    business_hours: Optional[str] = None
    total_chargers: Optional[int] = None
    available_chargers: Optional[int] = None
    charger_types: Optional[str] = None
    fee_description: Optional[str] = None
    parking_fee: Optional[str] = None


class ChargingStationResponse(ChargingStationBase):
    """Charging station response with metadata."""
    id: uuid.UUID
    data_updated_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class ChargingStationListResponse(BaseModel):
    """Paginated charging station list response."""
    total: int
    items: List[ChargingStationResponse]
    limit: int
    offset: int


class NearbyChargingResponse(ChargingStationResponse):
    """Nearby charging station with distance."""
    distance_meters: float = Field(
        ..., description="Distance from query point in meters"
    )


class NearbyChargingListResponse(BaseModel):
    """Nearby charging station list response."""
    items: List[NearbyChargingResponse]
    center_lat: float
    center_lng: float
    radius: int
