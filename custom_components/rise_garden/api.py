"""Rise Gardens API Client."""
import logging
import time
import requests
from typing import Any, Callable

from .const import (
    AUTH0_DOMAIN,
    CLIENT_ID,
    REALM,
    GRANT_TYPE,
    SCOPE,
    API_BASE,
)

_LOGGER = logging.getLogger(__name__)


class RiseGardensAPI:
    """Rise Gardens API Client."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the API client."""
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = 0
        self._on_token_refresh: Callable[[str], None] | None = None
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/3.14.9",
            "platform": "android",
            "version": "3.3.16",
        }

    def set_token_refresh_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback to be called when refresh token is rotated."""
        self._on_token_refresh = callback

    def set_tokens(self, access_token: str, refresh_token: str, expires_in: int = 36000) -> None:
        """Set tokens from stored values (for restoring session)."""
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = time.time() + expires_in
        self.headers["authorization"] = f"Bearer {self.access_token}"

    async def async_authenticate(self) -> bool:
        """Authenticate with Auth0 (sync wrapper for now)."""
        return self.authenticate()

    def authenticate(self) -> bool:
        """Authenticate with Auth0 and get access token."""
        url = f"https://{AUTH0_DOMAIN}/oauth/token"

        payload = {
            "username": self.username,
            "password": self.password,
            "realm": REALM,
            "scope": SCOPE,
            "client_id": CLIENT_ID,
            "grant_type": GRANT_TYPE
        }

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "auth0-client": "eyJuYW1lIjoicmVhY3QtbmF0aXZlLWF1dGgwIiwidmVyc2lvbiI6IjIuMTEuMCJ9",
            "User-Agent": "okhttp/3.14.9"
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                self._update_tokens(data)
                _LOGGER.info("Rise Gardens authentication successful")
                return True
            else:
                _LOGGER.error("Rise Gardens authentication failed: %s", response.text)
                return False
        except Exception as ex:
            _LOGGER.error("Rise Gardens authentication error: %s", ex)
            return False

    def refresh_access_token(self) -> bool:
        """Refresh access token using refresh token."""
        if not self.refresh_token:
            _LOGGER.warning("No refresh token available, re-authenticating")
            return self.authenticate()

        url = f"https://{AUTH0_DOMAIN}/oauth/token"

        payload = {
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": self.refresh_token,
        }

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "auth0-client": "eyJuYW1lIjoicmVhY3QtbmF0aXZlLWF1dGgwIiwidmVyc2lvbiI6IjIuMTEuMCJ9",
            "User-Agent": "okhttp/3.14.9"
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                self._update_tokens(data)
                _LOGGER.info("Rise Gardens token refresh successful")
                return True
            else:
                _LOGGER.warning("Token refresh failed (%s), re-authenticating", response.status_code)
                return self.authenticate()
        except Exception as ex:
            _LOGGER.error("Token refresh error: %s, re-authenticating", ex)
            return self.authenticate()

    def _update_tokens(self, data: dict) -> None:
        """Update tokens from API response."""
        self.access_token = data.get("access_token")
        new_refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 36000)  # Default 10 hours

        # Handle refresh token rotation
        if new_refresh_token and new_refresh_token != self.refresh_token:
            old_token = self.refresh_token
            self.refresh_token = new_refresh_token
            _LOGGER.debug("Refresh token rotated")
            # Notify callback so token can be persisted
            if self._on_token_refresh:
                self._on_token_refresh(new_refresh_token)
        elif new_refresh_token:
            self.refresh_token = new_refresh_token

        self.token_expires_at = time.time() + expires_in
        self.headers["authorization"] = f"Bearer {self.access_token}"

    def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token, refreshing if needed."""
        # Refresh if token expires in less than 5 minutes
        if time.time() > (self.token_expires_at - 300):
            _LOGGER.debug("Token expiring soon, refreshing")
            return self.refresh_access_token()
        return True

    def _api_request(
        self,
        method: str,
        url: str,
        retry_on_auth_fail: bool = True,
        **kwargs
    ) -> requests.Response | None:
        """Make an API request with automatic token refresh on 401."""
        self._ensure_valid_token()

        try:
            response = requests.request(method, url, headers=self.headers, timeout=30, **kwargs)

            # Handle 401 Unauthorized - token may have expired
            if response.status_code == 401 and retry_on_auth_fail:
                _LOGGER.info("Got 401, attempting token refresh")
                if self.refresh_access_token():
                    # Retry the request with new token
                    return self._api_request(method, url, retry_on_auth_fail=False, **kwargs)
                else:
                    _LOGGER.error("Token refresh failed, request unauthorized")
                    return None

            return response
        except Exception as ex:
            _LOGGER.error("API request error: %s", ex)
            return None

    def get_gardens_list(self) -> dict[str, Any] | None:
        """Get list of gardens."""
        url = f"{API_BASE}/gardens/list_v2"
        response = self._api_request("GET", url)
        if response and response.status_code == 200:
            return response.json()
        return None

    def get_gardens_device_data(self) -> dict[str, Any] | None:
        """Get device data for all gardens."""
        url = f"{API_BASE}/gardens/gardens_device_data"
        response = self._api_request("GET", url)
        if response and response.status_code == 200:
            return response.json()
        return None

    def get_light_schedule(self, garden_id: int) -> dict[str, Any] | None:
        """Get light schedule for a garden."""
        url = f"{API_BASE}/device/light-schedule"
        response = self._api_request("GET", url, params={"garden_id": garden_id})
        if response and response.status_code == 200:
            return response.json()
        return None

    def set_light_level(self, garden_id: int, level: int) -> bool:
        """Set light intensity (0-100)."""
        url = f"{API_BASE}/gardens/{garden_id}/device/light-level"
        response = self._api_request("PUT", url, json={"light_level": level})
        return response is not None and response.status_code == 200

    def get_last_sensor_data(self, garden_id: int) -> dict[str, Any] | None:
        """Get last sensor data for a garden."""
        url = f"{API_BASE}/device/last_data_sensors"
        response = self._api_request("GET", url, params={"garden_id": garden_id})
        if response and response.status_code == 200:
            return response.json()
        return None

    def set_pump(self, garden_id: int, on: bool = True) -> bool:
        """Turn pump on or off."""
        url = f"{API_BASE}/gardens/{garden_id}/device/pump"
        response = self._api_request("POST", url, json={"pump": on})
        return response is not None and response.status_code == 200

    def get_pump_schedule(self, garden_id: int) -> dict[str, Any] | None:
        """Get pump schedule for a garden."""
        url = f"{API_BASE}/device/pump/schedule"
        response = self._api_request("GET", url, params={"garden_id": garden_id})
        if response and response.status_code == 200:
            return response.json()
        return None
