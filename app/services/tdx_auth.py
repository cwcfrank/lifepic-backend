"""
TDX Authentication Service.
Handles OIDC Client Credentials flow for TDX API access.
"""
import time
from typing import Optional
import httpx
from app.config import get_settings


class TDXAuthService:
    """Service for TDX API authentication."""
    
    def __init__(self):
        self.settings = get_settings()
        self._token: Optional[str] = None
        self._token_expires_at: float = 0
    
    async def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        Token is cached for efficiency.
        """
        # Return cached token if still valid (with 5 minute buffer)
        if self._token and time.time() < (self._token_expires_at - 300):
            return self._token
        
        # Request new token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.settings.tdx_auth_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.settings.tdx_client_id,
                    "client_secret": self.settings.tdx_client_secret,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            
            token_data = response.json()
            self._token = token_data["access_token"]
            # TDX tokens are valid for 86400 seconds (1 day)
            expires_in = token_data.get("expires_in", 86400)
            self._token_expires_at = time.time() + expires_in
            
            return self._token
    
    def get_auth_headers(self, token: str) -> dict:
        """Get authorization headers for TDX API requests."""
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }


# Singleton instance
_tdx_auth_service: Optional[TDXAuthService] = None


def get_tdx_auth_service() -> TDXAuthService:
    """Get TDX auth service singleton."""
    global _tdx_auth_service
    if _tdx_auth_service is None:
        _tdx_auth_service = TDXAuthService()
    return _tdx_auth_service
