"""
Google Maps Geocoding Service.
Uses Google Maps Geocoding API to convert addresses to coordinates.
"""
from typing import Optional, Tuple
import httpx
from app.config import get_settings


class GeocodingService:
    """Service for geocoding addresses using Google Maps API."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"

    async def geocode_address(
        self, address: str, city: str = ""
    ) -> Optional[Tuple[float, float]]:
        """
        Geocode an address to get latitude and longitude.
        Returns (latitude, longitude) or None if not found.
        """
        data = await self.get_raw_response(address, city)
        if data and data.get("status") == "OK" and data.get("results"):
            location = data["results"][0]["geometry"]["location"]
            return (location["lat"], location["lng"])
        return None

    async def get_raw_response(
        self, address: str, city: str = ""
    ) -> Optional[dict]:
        """Get raw response from Google Maps API for debugging."""
        if not self.settings.google_maps_api_key:
            return {"status": "ERROR", "error_message": "No API Key"}

        # Build search query
        query = address if address else ""
        if city and city not in query:
            query = f"{query}, {city}, Taiwan"
        elif "Taiwan" not in query and "台灣" not in query:
            query = f"{query}, Taiwan"

        if not query.strip():
            return {"status": "INVALID_REQUEST", "error_message": "Empty address"}

        params = {
            "address": query,
            "key": self.settings.google_maps_api_key,
            "language": "zh-TW",
            "region": "tw",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    timeout=10.0,
                )
                # Don't raise for status, we want to see 403/400 bodies
                return response.json()

        except Exception as e:
            return {"status": "EXCEPTION", "error_message": str(e)}

    async def geocode_by_name(
        self, name: str, city: str = ""
    ) -> Optional[Tuple[float, float]]:
        """
        Geocode by station name (fallback when address is empty).
        """
        # Map city codes to Chinese names for better results
        city_names = {
            "Taipei": "台北市",
            "NewTaipei": "新北市",
            "Taoyuan": "桃園市",
            "Taichung": "台中市",
            "Tainan": "台南市",
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
            "TaitungCounty": "台東縣",
            "KinmenCounty": "金門縣",
            "PenghuCounty": "澎湖縣",
            "LienchiangCounty": "連江縣",
        }

        city_zh = city_names.get(city, city)
        query = f"{name} {city_zh}"

        return await self.geocode_address(query)


# Singleton instance
_geocoding_service: Optional[GeocodingService] = None


def get_geocoding_service() -> GeocodingService:
    """Get geocoding service singleton."""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service
