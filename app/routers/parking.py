"""
Parking data API router.
Provides endpoints for querying parking lot data.
"""
import math
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.database import get_db
from app.models.parking import ParkingLot
from app.schemas.parking import (
    ParkingLotResponse,
    ParkingLotListResponse,
    NearbyParkingResponse,
    NearbyParkingListResponse,
    CityInfo,
    CityListResponse,
)
from app.services.tdx_parking import SUPPORTED_CITIES

router = APIRouter(prefix="/api/parking", tags=["Parking"])


@router.get("/cities", response_model=CityListResponse)
async def get_cities():
    """Get list of supported cities."""
    cities = [
        CityInfo(code=code, name_zh=info["zh"], name_en=info["en"])
        for code, info in SUPPORTED_CITIES.items()
    ]
    return CityListResponse(cities=cities)


@router.get("", response_model=ParkingLotListResponse)
async def get_parking_lots(
    city: Optional[str] = Query(None, description="Filter by city code"),
    has_available: Optional[bool] = Query(None, description="Filter with available spaces"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated list of parking lots.
    Supports filtering by city and availability.
    """
    # Build query
    query = select(ParkingLot)
    count_query = select(func.count(ParkingLot.id))
    
    # Apply filters
    filters = []
    if city:
        filters.append(ParkingLot.city == city)
    if has_available is True:
        filters.append(ParkingLot.available_spaces > 0)
    elif has_available is False:
        filters.append(ParkingLot.available_spaces == 0)
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination and ordering
    query = query.order_by(ParkingLot.city, ParkingLot.name).offset(offset).limit(limit)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return ParkingLotListResponse(
        total=total,
        items=[ParkingLotResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
    )


@router.get("/nearby", response_model=NearbyParkingListResponse)
async def get_nearby_parking(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius: int = Query(1000, ge=100, le=10000, description="Radius in meters"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get parking lots near a location.
    Uses Haversine formula for distance calculation.
    """
    # Haversine formula for distance calculation
    # Convert radius to approximate degrees (1 degree ≈ 111km at equator)
    lat_range = radius / 111000
    lng_range = radius / (111000 * math.cos(math.radians(lat)))
    
    # First filter by bounding box for efficiency
    query = select(ParkingLot).where(
        and_(
            ParkingLot.latitude.isnot(None),
            ParkingLot.longitude.isnot(None),
            ParkingLot.latitude.between(lat - lat_range, lat + lat_range),
            ParkingLot.longitude.between(lng - lng_range, lng + lng_range),
        )
    )
    
    result = await db.execute(query)
    candidates = result.scalars().all()
    
    # Calculate actual distances and filter
    nearby_items = []
    for parking in candidates:
        if parking.latitude and parking.longitude:
            distance = haversine_distance(lat, lng, parking.latitude, parking.longitude)
            if distance <= radius:
                nearby_items.append((parking, distance))
    
    # Sort by distance and limit
    nearby_items.sort(key=lambda x: x[1])
    nearby_items = nearby_items[:limit]
    
    return NearbyParkingListResponse(
        items=[
            NearbyParkingResponse(
                **ParkingLotResponse.model_validate(item[0]).model_dump(),
                distance_meters=round(item[1], 2),
            )
            for item in nearby_items
        ],
        center_lat=lat,
        center_lng=lng,
        radius=radius,
    )


@router.get("/{park_id}", response_model=ParkingLotResponse)
async def get_parking_lot(
    park_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get single parking lot by ID."""
    query = select(ParkingLot).where(ParkingLot.park_id == park_id)
    result = await db.execute(query)
    parking = result.scalar_one_or_none()
    
    if not parking:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    
    return ParkingLotResponse.model_validate(parking)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points (in meters).
    Uses Haversine formula.
    """
    R = 6371000  # Earth's radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c
