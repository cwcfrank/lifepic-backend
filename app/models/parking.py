"""
Parking data models for SQLAlchemy ORM.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ParkingLot(Base):
    """Parking lot information from TDX API."""
    
    __tablename__ = "parking_lots"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # TDX identifiers
    park_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    
    # Basic info
    name: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(50), index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Location
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Capacity
    total_spaces: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_spaces: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Additional info
    fare_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parking_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 路外/路邊
    
    # Timestamps
    data_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Indexes for location-based queries
    __table_args__ = (
        Index('idx_parking_location', 'latitude', 'longitude'),
    )


class SyncStatus(Base):
    """Track data synchronization status."""
    
    __tablename__ = "sync_status"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    last_sync_at: Mapped[datetime] = mapped_column(DateTime)
    records_synced: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="success")  # success, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
