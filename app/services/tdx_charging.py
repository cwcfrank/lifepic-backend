"""
TDX Charging Station Data Service.
Fetches charging station data from TDX API.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from app.config import get_settings
from app.services.tdx_auth import get_tdx_auth_service


class TDXChargingService:
    """Service for fetching charging station data from TDX API."""

    def __init__(self):
        self.settings = get_settings()
        self.auth_service = get_tdx_auth_service()
        self.base_url = self.settings.tdx_api_base_url

    async def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Any:
        """Make authenticated request to TDX API."""
        token = await self.auth_service.get_access_token()
        headers = self.auth_service.get_auth_headers(token)

        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                params=params,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_charging_stations(self) -> List[Dict[str, Any]]:
        """
        Get all charging station data.
        Endpoint: /v1/CityEVCharging/ChargingStation
        """
        endpoint = "/v1/CityEVCharging/ChargingStation"
        params = {"$format": "JSON"}

        try:
            data = await self._make_request(endpoint, params)
            if isinstance(data, list):
                return data
            return data.get("ChargingStations", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise

    async def get_charging_availability(self) -> List[Dict[str, Any]]:
        """
        Get charging station availability.
        Endpoint: /v1/CityEVCharging/ChargingStationAvailability
        """
        endpoint = "/v1/CityEVCharging/ChargingStationAvailability"
        params = {"$format": "JSON"}

        try:
            data = await self._make_request(endpoint, params)
            if isinstance(data, list):
                return data
            return data.get("ChargingStationAvailabilities", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise

    def parse_charging_station(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse TDX charging station data into our model format."""
        # Extract position
        position = data.get("StationPosition", {})
        lat = position.get("PositionLat")
        lng = position.get("PositionLon")

        # Extract name (prefer Chinese)
        name = data.get("StationName", {})
        if isinstance(name, dict):
            name = name.get("Zh_tw") or name.get("En") or "Unknown"

        # Extract address
        address = data.get("Address", "")
        if isinstance(address, dict):
            address = address.get("Zh_tw") or address.get("En") or ""

        # Extract city from address or location
        city = data.get("City", "")
        if isinstance(city, dict):
            city = city.get("Zh_tw") or city.get("En") or ""

        # Extract operator
        operator = data.get("OperatorName", "")
        if isinstance(operator, dict):
            operator = operator.get("Zh_tw") or operator.get("En") or ""

        # Extract charger types
        chargers = data.get("Chargers", [])
        charger_types = []
        total_chargers = 0
        for charger in chargers:
            charger_type = charger.get("ChargerType", "")
            count = charger.get("Count", 1)
            total_chargers += count
            if charger_type:
                charger_types.append(f"{charger_type}x{count}")

        # Extract fee info
        fee_desc = data.get("FeeDescription", "")
        if isinstance(fee_desc, dict):
            fee_desc = fee_desc.get("Zh_tw") or fee_desc.get("En") or ""

        return {
            "station_id": data.get("StationID", ""),
            "name": name,
            "address": address,
            "city": city if city else None,
            "latitude": lat,
            "longitude": lng,
            "operator_name": operator if operator else None,
            "phone": data.get("Phone"),
            "is_24h": data.get("Is24H"),
            "business_hours": data.get("BusinessHours"),
            "total_chargers": total_chargers if total_chargers > 0 else None,
            "charger_types": ", ".join(charger_types) if charger_types else None,
            "fee_description": fee_desc if fee_desc else None,
            "parking_fee": data.get("ParkingFee"),
        }

    def merge_availability(
        self,
        station: Dict[str, Any],
        availability_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge availability data into charging station data."""
        station_id = station["station_id"]
        if station_id in availability_map:
            avail = availability_map[station_id]
            station["available_chargers"] = avail.get("AvailableChargers")

            # Parse update time and convert to naive UTC
            update_time = (
                avail.get("DataCollectTime") or avail.get("SrcUpdateTime")
            )
            if update_time:
                try:
                    dt = datetime.fromisoformat(
                        update_time.replace("Z", "+00:00")
                    )
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                    station["data_updated_at"] = dt
                except (ValueError, AttributeError):
                    pass

        return station


# Singleton instance
_tdx_charging_service: Optional[TDXChargingService] = None


def get_tdx_charging_service() -> TDXChargingService:
    """Get TDX charging service singleton."""
    global _tdx_charging_service
    if _tdx_charging_service is None:
        _tdx_charging_service = TDXChargingService()
    return _tdx_charging_service
