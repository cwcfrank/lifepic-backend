"""
TDX Parking Data Service.
Fetches parking lot data from TDX API.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from app.config import get_settings
from app.services.tdx_auth import get_tdx_auth_service


# Supported cities in Taiwan
SUPPORTED_CITIES = {
    "Taipei": {"zh": "臺北市", "en": "Taipei City"},
    "NewTaipei": {"zh": "新北市", "en": "New Taipei City"},
    "Taoyuan": {"zh": "桃園市", "en": "Taoyuan City"},
    "Taichung": {"zh": "臺中市", "en": "Taichung City"},
    "Tainan": {"zh": "臺南市", "en": "Tainan City"},
    "Kaohsiung": {"zh": "高雄市", "en": "Kaohsiung City"},
    "Keelung": {"zh": "基隆市", "en": "Keelung City"},
    "Hsinchu": {"zh": "新竹市", "en": "Hsinchu City"},
    "HsinchuCounty": {"zh": "新竹縣", "en": "Hsinchu County"},
    "MiaoliCounty": {"zh": "苗栗縣", "en": "Miaoli County"},
    "ChanghuaCounty": {"zh": "彰化縣", "en": "Changhua County"},
    "NantouCounty": {"zh": "南投縣", "en": "Nantou County"},
    "YunlinCounty": {"zh": "雲林縣", "en": "Yunlin County"},
    "ChiayiCounty": {"zh": "嘉義縣", "en": "Chiayi County"},
    "Chiayi": {"zh": "嘉義市", "en": "Chiayi City"},
    "PingtungCounty": {"zh": "屏東縣", "en": "Pingtung County"},
    "YilanCounty": {"zh": "宜蘭縣", "en": "Yilan County"},
    "HualienCounty": {"zh": "花蓮縣", "en": "Hualien County"},
    "TaitungCounty": {"zh": "臺東縣", "en": "Taitung County"},
    "PenghuCounty": {"zh": "澎湖縣", "en": "Penghu County"},
    "KinmenCounty": {"zh": "金門縣", "en": "Kinmen County"},
    "LienchiangCounty": {"zh": "連江縣", "en": "Lienchiang County"},
}


class TDXParkingService:
    """Service for fetching parking data from TDX API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.auth_service = get_tdx_auth_service()
        self.base_url = self.settings.tdx_api_base_url
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
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
    
    async def get_parking_lots(self, city: str) -> List[Dict[str, Any]]:
        """
        Get parking lot basic information for a city.
        Endpoint: /v1/Parking/OffStreet/CarPark/City/{City}
        """
        endpoint = f"/v1/Parking/OffStreet/CarPark/City/{city}"
        params = {"$format": "JSON"}
        
        try:
            data = await self._make_request(endpoint, params)
            return data if isinstance(data, list) else data.get("CarParks", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []  # City might not have data
            raise
    
    async def get_parking_availability(self, city: str) -> List[Dict[str, Any]]:
        """
        Get real-time parking availability for a city.
        Endpoint: /v1/Parking/OffStreet/ParkingAvailability/City/{City}
        """
        endpoint = f"/v1/Parking/OffStreet/ParkingAvailability/City/{city}"
        params = {"$format": "JSON"}
        
        try:
            data = await self._make_request(endpoint, params)
            return data if isinstance(data, list) else data.get("ParkingAvailabilities", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise
    
    def parse_parking_lot(self, data: Dict[str, Any], city: str) -> Dict[str, Any]:
        """Parse TDX parking lot data into our model format."""
        # Extract position
        position = data.get("CarParkPosition", {})
        lat = position.get("PositionLat")
        lng = position.get("PositionLon")
        
        # Extract name (prefer Chinese)
        name = data.get("CarParkName", {})
        if isinstance(name, dict):
            name = name.get("Zh_tw") or name.get("En") or "Unknown"
        
        # Extract address
        address = data.get("Address", "")
        if isinstance(address, dict):
            address = address.get("Zh_tw") or address.get("En") or ""
        
        # Extract fare info
        fare_desc = data.get("FareDescription", "")
        if isinstance(fare_desc, dict):
            fare_desc = fare_desc.get("Zh_tw") or fare_desc.get("En") or ""
        
        return {
            "park_id": data.get("CarParkID", ""),
            "name": name,
            "city": city,
            "address": address,
            "latitude": lat,
            "longitude": lng,
            "total_spaces": data.get("TotalSpaces"),
            "fare_description": fare_desc,
            "parking_type": "OffStreet",
        }
    
    def merge_availability(
        self,
        parking_lot: Dict[str, Any],
        availability_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge availability data into parking lot data."""
        park_id = parking_lot["park_id"]
        if park_id in availability_map:
            avail = availability_map[park_id]
            parking_lot["available_spaces"] = avail.get("AvailableSpaces")

            # Parse update time and convert to naive UTC datetime
            update_time = avail.get("DataCollectTime") or avail.get("SrcUpdateTime")
            if update_time:
                try:
                    dt = datetime.fromisoformat(
                        update_time.replace("Z", "+00:00")
                    )
                    # Convert to naive UTC datetime for PostgreSQL
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                    parking_lot["data_updated_at"] = dt
                except (ValueError, AttributeError):
                    pass

        return parking_lot


# Singleton instance
_tdx_parking_service: Optional[TDXParkingService] = None


def get_tdx_parking_service() -> TDXParkingService:
    """Get TDX parking service singleton."""
    global _tdx_parking_service
    if _tdx_parking_service is None:
        _tdx_parking_service = TDXParkingService()
    return _tdx_parking_service
