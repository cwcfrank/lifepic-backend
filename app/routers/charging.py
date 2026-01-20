"""
Charging station API router.
Provides endpoints for querying charging station data.
"""
import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.database import get_db
from app.models.charging import ChargingStation
from app.schemas.charging import (
    ChargingStationResponse,
    ChargingStationListResponse,
    NearbyChargingResponse,
    NearbyChargingListResponse,
)

router = APIRouter(prefix="/api/charging", tags=["Charging"])


@router.get("", response_model=ChargingStationListResponse)
async def get_charging_stations(
    city: Optional[str] = Query(None, description="Filter by city"),
    has_available: Optional[bool] = Query(
        None, description="Filter with available chargers"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated list of charging stations.
    Supports filtering by city and availability.
    """
    query = select(ChargingStation)
    count_query = select(func.count(ChargingStation.id))

    filters = []
    if city:
        filters.append(ChargingStation.city == city)
    if has_available is True:
        filters.append(ChargingStation.available_chargers > 0)
    elif has_available is False:
        filters.append(ChargingStation.available_chargers == 0)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ChargingStation.name).offset(offset).limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()

    return ChargingStationListResponse(
        total=total,
        items=[ChargingStationResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
    )


@router.get("/nearby", response_model=NearbyChargingListResponse)
async def get_nearby_charging(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius: int = Query(
        1000, ge=100, le=10000, description="Radius in meters"
    ),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get charging stations near a location.
    Uses Haversine formula for distance calculation.
    """
    lat_range = radius / 111000
    lng_range = radius / (111000 * math.cos(math.radians(lat)))

    query = select(ChargingStation).where(
        and_(
            ChargingStation.latitude.isnot(None),
            ChargingStation.longitude.isnot(None),
            ChargingStation.latitude.between(lat - lat_range, lat + lat_range),
            ChargingStation.longitude.between(lng - lng_range, lng + lng_range),
        )
    )

    result = await db.execute(query)
    candidates = result.scalars().all()

    nearby_items = []
    for station in candidates:
        if station.latitude and station.longitude:
            distance = haversine_distance(
                lat, lng, station.latitude, station.longitude
            )
            if distance <= radius:
                nearby_items.append((station, distance))

    nearby_items.sort(key=lambda x: x[1])
    nearby_items = nearby_items[:limit]

    return NearbyChargingListResponse(
        items=[
            NearbyChargingResponse(
                **ChargingStationResponse.model_validate(item[0]).model_dump(),
                distance_meters=round(item[1], 2),
            )
            for item in nearby_items
        ],
        center_lat=lat,
        center_lng=lng,
        radius=radius,
    )


@router.get("/{station_id}", response_model=ChargingStationResponse)
async def get_charging_station(
    station_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get single charging station by ID."""
    query = select(ChargingStation).where(
        ChargingStation.station_id == station_id
    )
    result = await db.execute(query)
    station = result.scalar_one_or_none()

    if not station:
        raise HTTPException(status_code=404, detail="Charging station not found")

    return ChargingStationResponse.model_validate(station)


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate the great circle distance between two points (in meters).
    Uses Haversine formula.
    """
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
