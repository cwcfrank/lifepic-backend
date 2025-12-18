"""
Data sync API router.
Provides endpoints for triggering and monitoring data synchronization.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from app.database import get_db
from app.config import get_settings
from app.models.parking import ParkingLot, SyncStatus
from app.models.charging import ChargingStation
from app.schemas.parking import (
    SyncTriggerRequest,
    SyncStatusResponse,
    SyncResultResponse,
)
from app.services.tdx_parking import get_tdx_parking_service, SUPPORTED_CITIES
from app.services.tdx_charging import get_tdx_charging_service

router = APIRouter(prefix="/api/sync", tags=["Sync"])


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify API key for sync endpoints."""
    settings = get_settings()
    if x_api_key != settings.sync_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


@router.post("/trigger", response_model=SyncResultResponse)
async def trigger_sync(
    request: SyncTriggerRequest = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """
    Trigger data synchronization from TDX API.
    Requires X-API-Key header for authentication.
    """
    # Determine which cities to sync
    cities_to_sync = request.cities if request and request.cities else list(SUPPORTED_CITIES.keys())
    
    # Validate city codes
    invalid_cities = [c for c in cities_to_sync if c not in SUPPORTED_CITIES]
    if invalid_cities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid city codes: {invalid_cities}"
        )
    
    # Run sync
    total_records = 0
    synced_cities = []
    
    parking_service = get_tdx_parking_service()
    
    for city in cities_to_sync:
        try:
            # Fetch data from TDX
            parking_lots = await parking_service.get_parking_lots(city)
            availability = await parking_service.get_parking_availability(city)
            
            # Create availability lookup map
            availability_map = {
                item.get("CarParkID"): item 
                for item in availability 
                if item.get("CarParkID")
            }
            
            # Process and upsert parking lots
            records_synced = 0
            for lot_data in parking_lots:
                parsed = parking_service.parse_parking_lot(lot_data, city)
                parsed = parking_service.merge_availability(parsed, availability_map)
                
                if not parsed["park_id"]:
                    continue
                
                # Upsert parking lot
                stmt = insert(ParkingLot).values(
                    park_id=parsed["park_id"],
                    name=parsed["name"],
                    city=parsed["city"],
                    address=parsed.get("address"),
                    latitude=parsed.get("latitude"),
                    longitude=parsed.get("longitude"),
                    total_spaces=parsed.get("total_spaces"),
                    available_spaces=parsed.get("available_spaces"),
                    fare_description=parsed.get("fare_description"),
                    parking_type=parsed.get("parking_type"),
                    data_updated_at=parsed.get("data_updated_at"),
                    updated_at=datetime.utcnow(),
                ).on_conflict_do_update(
                    index_elements=["park_id"],
                    set_={
                        "name": parsed["name"],
                        "address": parsed.get("address"),
                        "latitude": parsed.get("latitude"),
                        "longitude": parsed.get("longitude"),
                        "total_spaces": parsed.get("total_spaces"),
                        "available_spaces": parsed.get("available_spaces"),
                        "fare_description": parsed.get("fare_description"),
                        "data_updated_at": parsed.get("data_updated_at"),
                        "updated_at": datetime.utcnow(),
                    }
                )
                await db.execute(stmt)
                records_synced += 1
            
            # Update sync status
            sync_status_stmt = insert(SyncStatus).values(
                city=city,
                last_sync_at=datetime.utcnow(),
                records_synced=records_synced,
                status="success",
            ).on_conflict_do_update(
                index_elements=["city"],
                set_={
                    "last_sync_at": datetime.utcnow(),
                    "records_synced": records_synced,
                    "status": "success",
                    "error_message": None,
                }
            )
            await db.execute(sync_status_stmt)
            
            await db.commit()
            total_records += records_synced
            synced_cities.append(city)
            
        except Exception as e:
            # Log error and update sync status
            error_msg = str(e)
            sync_status_stmt = insert(SyncStatus).values(
                city=city,
                last_sync_at=datetime.utcnow(),
                records_synced=0,
                status="failed",
                error_message=error_msg,
            ).on_conflict_do_update(
                index_elements=["city"],
                set_={
                    "last_sync_at": datetime.utcnow(),
                    "status": "failed",
                    "error_message": error_msg,
                }
            )
            await db.execute(sync_status_stmt)
            await db.commit()
    
    return SyncResultResponse(
        success=len(synced_cities) > 0,
        message=f"Synced {len(synced_cities)} cities with {total_records} total records",
        synced_cities=synced_cities,
        total_records=total_records,
    )


@router.get("/status", response_model=List[SyncStatusResponse])
async def get_sync_status(
    city: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get sync status for all or specific cities."""
    query = select(SyncStatus)
    if city:
        query = query.where(SyncStatus.city == city)
    query = query.order_by(SyncStatus.city)
    
    result = await db.execute(query)
    statuses = result.scalars().all()
    
    return [
        SyncStatusResponse(
            city=s.city,
            last_sync_at=s.last_sync_at,
            records_synced=s.records_synced,
            status=s.status,
            error_message=s.error_message,
        )
        for s in statuses
    ]


@router.post("/charging", response_model=SyncResultResponse)
async def trigger_charging_sync(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """
    Trigger charging station synchronization from TDX API.
    Requires X-API-Key header for authentication.
    """
    charging_service = get_tdx_charging_service()

    try:
        # Fetch charging station data
        stations = await charging_service.get_charging_stations()
        availability = await charging_service.get_charging_availability()

        # Create availability lookup map
        availability_map = {
            item.get("StationID"): item
            for item in availability
            if item.get("StationID")
        }

        # Process and upsert charging stations
        records_synced = 0
        for station_data in stations:
            parsed = charging_service.parse_charging_station(station_data)
            parsed = charging_service.merge_availability(parsed, availability_map)

            if not parsed["station_id"]:
                continue

            # Upsert charging station
            stmt = insert(ChargingStation).values(
                station_id=parsed["station_id"],
                name=parsed["name"],
                address=parsed.get("address"),
                city=parsed.get("city"),
                latitude=parsed.get("latitude"),
                longitude=parsed.get("longitude"),
                operator_name=parsed.get("operator_name"),
                phone=parsed.get("phone"),
                is_24h=parsed.get("is_24h"),
                business_hours=parsed.get("business_hours"),
                total_chargers=parsed.get("total_chargers"),
                available_chargers=parsed.get("available_chargers"),
                charger_types=parsed.get("charger_types"),
                fee_description=parsed.get("fee_description"),
                parking_fee=parsed.get("parking_fee"),
                data_updated_at=parsed.get("data_updated_at"),
                updated_at=datetime.utcnow(),
            ).on_conflict_do_update(
                index_elements=["station_id"],
                set_={
                    "name": parsed["name"],
                    "address": parsed.get("address"),
                    "city": parsed.get("city"),
                    "latitude": parsed.get("latitude"),
                    "longitude": parsed.get("longitude"),
                    "operator_name": parsed.get("operator_name"),
                    "phone": parsed.get("phone"),
                    "is_24h": parsed.get("is_24h"),
                    "business_hours": parsed.get("business_hours"),
                    "total_chargers": parsed.get("total_chargers"),
                    "available_chargers": parsed.get("available_chargers"),
                    "charger_types": parsed.get("charger_types"),
                    "fee_description": parsed.get("fee_description"),
                    "parking_fee": parsed.get("parking_fee"),
                    "data_updated_at": parsed.get("data_updated_at"),
                    "updated_at": datetime.utcnow(),
                }
            )
            await db.execute(stmt)
            records_synced += 1

        await db.commit()

        return SyncResultResponse(
            success=True,
            message=f"Synced {records_synced} charging stations",
            synced_cities=["All"],
            total_records=records_synced,
        )

    except Exception as e:
        await db.rollback()
        return SyncResultResponse(
            success=False,
            message=f"Charging sync failed: {str(e)}",
            synced_cities=[],
            total_records=0,
        )

