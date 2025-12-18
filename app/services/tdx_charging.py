"""
TDX Charging Station Data Service.
Fetches charging station data from TDX API.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from app.config import get_settings
from app.services.tdx_auth import get_tdx_auth_service


# Supported cities for EV charging data (same as parking)
SUPPORTED_CITIES_EV = {
    "Taipei": "臺北市",
    "NewTaipei": "新北市",
    "Taoyuan": "桃園市",
    "Taichung": "臺中市",
    "Tainan": "臺南市",
    "Kaohsiung": "高雄市",
    "Keelung": "基隆市",
    "Hsinchu": "新竹市",
    "HsinchuCounty": "新竹縣",
    "MiaoliCounty": "苗栗縣",
    "ChanghuaCounty": "彰化縣",
    "NantouCounty": "南投縣",
    "YunlinCounty": "雲林縣",
    "ChiayiCounty": "嘉義縣",
    "Chiayi": "嘉義市",
    "PingtungCounty": "屏東縣",
    "YilanCounty": "宜蘭縣",
    "HualienCounty": "花蓮縣",
    "TaitungCounty": "臺東縣",
    "PenghuCounty": "澎湖縣",
    "KinmenCounty": "金門縣",
    "LienchiangCounty": "連江縣",
}


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

    async def get_charging_stations_by_city(
        self, city: str
    ) -> List[Dict[str, Any]]:
        """
        Get charging station data for a specific city.
        Endpoint: /v1/EV/Station/City/{City}
        """
        endpoint = f"/v1/EV/Station/City/{city}"
        params = {"$format": "JSON"}

        try:
            data = await self._make_request(endpoint, params)
            if isinstance(data, list):
                return data
            # Try different response keys
            return (
                data.get("Stations", [])
                or data.get("EVStations", [])
                or data.get("ChargingStations", [])
                or []
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise

    async def get_connector_status_by_city(
        self, city: str
    ) -> List[Dict[str, Any]]:
        """
        Get charging connector live status for a specific city.
        Endpoint: /v1/EV/ConnectorLiveStatus/City/{City}
        """
        endpoint = f"/v1/EV/ConnectorLiveStatus/City/{city}"
        params = {"$format": "JSON"}

        try:
            data = await self._make_request(endpoint, params)
            if isinstance(data, list):
                return data
            return (
                data.get("ConnectorLiveStatuses", [])
                or data.get("Statuses", [])
                or []
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise

    def parse_charging_station(
        self, data: Dict[str, Any], city: str
    ) -> Dict[str, Any]:
        """Parse TDX EV charging station data into our model format."""
        # Extract position
        position = data.get("Position", {})
        lat = position.get("PositionLat")
        lng = position.get("PositionLon")

        # Extract name (prefer Chinese)
        name = data.get("StationName", {})
        if isinstance(name, dict):
            name = name.get("Zh_tw") or name.get("En") or "Unknown"
        elif not name:
            name = "Unknown"

        # Extract address
        address = data.get("Address", "")
        if isinstance(address, dict):
            address = address.get("Zh_tw") or address.get("En") or ""

        # Extract operator
        operator = data.get("OperatorName", "")
        if isinstance(operator, dict):
            operator = operator.get("Zh_tw") or operator.get("En") or ""

        # Extract connector info
        connectors = data.get("Connectors", [])
        connector_types = []
        total_connectors = 0
        for conn in connectors:
            conn_type = conn.get("ConnectorType", "")
            if conn_type:
                connector_types.append(conn_type)
            total_connectors += 1

        # Extract fee info
        fee_desc = data.get("ChargingFee", "")
        if isinstance(fee_desc, dict):
            fee_desc = fee_desc.get("Zh_tw") or fee_desc.get("En") or ""

        parking_fee = data.get("ParkingFee", "")
        if isinstance(parking_fee, dict):
            parking_fee = parking_fee.get("Zh_tw") or parking_fee.get("En") or ""

        return {
            "station_id": data.get("StationID", ""),
            "name": name,
            "address": address,
            "city": city,
            "latitude": lat,
            "longitude": lng,
            "operator_name": operator if operator else None,
            "phone": data.get("Phone"),
            "is_24h": data.get("Is24Hours"),
            "business_hours": data.get("ServiceTime"),
            "total_chargers": total_connectors if total_connectors > 0 else None,
            "charger_types": ", ".join(set(connector_types)) if connector_types else None,
            "fee_description": fee_desc if fee_desc else None,
            "parking_fee": parking_fee if parking_fee else None,
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
            # Count available connectors
            available = sum(
                1 for s in avail.get("Connectors", [])
                if s.get("Status") == "Available"
            )
            station["available_chargers"] = available

            # Parse update time
            update_time = avail.get("UpdateTime") or avail.get("SrcUpdateTime")
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
