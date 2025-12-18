"""
Charging station data models for SQLAlchemy ORM.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ChargingStation(Base):
    """Charging station information from TDX API."""

    __tablename__ = "charging_stations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # TDX identifiers
    station_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)

    # Location
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Station details
    operator_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_24h: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    business_hours: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Charger info
    total_chargers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_chargers: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Charger types (JSON-like string for simplicity)
    charger_types: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Pricing
    fee_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parking_fee: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    data_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Indexes for location-based queries
    __table_args__ = (
        Index('idx_charging_location', 'latitude', 'longitude'),
    )
