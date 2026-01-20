"""
Pydantic schemas for parking data API.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


# ============ Request Schemas ============

class ParkingQueryParams(BaseModel):
    """Query parameters for parking list endpoint."""
    city: Optional[str] = Field(None, description="Filter by city code")
    limit: int = Field(50, ge=1, le=200, description="Number of results")
    offset: int = Field(0, ge=0, description="Pagination offset")
    has_available: Optional[bool] = Field(None, description="Filter parking with available spaces")


class NearbyQueryParams(BaseModel):
    """Query parameters for nearby parking endpoint."""
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")
    radius: int = Field(1000, ge=100, le=10000, description="Search radius in meters")
    limit: int = Field(20, ge=1, le=100, description="Number of results")


# ============ Response Schemas ============

class ParkingLotBase(BaseModel):
    """Base parking lot schema."""
    park_id: str
    name: str
    city: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_spaces: Optional[int] = None
    available_spaces: Optional[int] = None
    fare_description: Optional[str] = None
    parking_type: Optional[str] = None


class ParkingLotResponse(ParkingLotBase):
    """Parking lot response with metadata."""
    id: uuid.UUID
    data_updated_at: Optional[datetime] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ParkingLotListResponse(BaseModel):
    """Paginated parking lot list response."""
    total: int
    items: List[ParkingLotResponse]
    limit: int
    offset: int


class NearbyParkingResponse(ParkingLotResponse):
    """Nearby parking with distance."""
    distance_meters: float = Field(..., description="Distance from query point in meters")


class NearbyParkingListResponse(BaseModel):
    """Nearby parking list response."""
    items: List[NearbyParkingResponse]
    center_lat: float
    center_lng: float
    radius: int


# ============ City Schema ============

class CityInfo(BaseModel):
    """City information."""
    code: str
    name_zh: str
    name_en: str


class CityListResponse(BaseModel):
    """List of supported cities."""
    cities: List[CityInfo]


# ============ Sync Schemas ============

class SyncTriggerRequest(BaseModel):
    """Request to trigger sync for specific cities."""
    cities: Optional[List[str]] = Field(None, description="Cities to sync, null for all")


class SyncStatusResponse(BaseModel):
    """Sync status response."""
    city: str
    last_sync_at: Optional[datetime] = None
    records_synced: int = 0
    status: str = "pending"
    error_message: Optional[str] = None


class SyncResultResponse(BaseModel):
    """Result of sync operation."""
    success: bool
    message: str
    synced_cities: List[str]
    total_records: int
