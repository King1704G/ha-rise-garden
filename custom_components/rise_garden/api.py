"""Rise Gardens API Client."""
import logging
import requests
from typing import Any

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
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/3.14.9",
            "platform": "android",
            "version": "3.3.16",
        }

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
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.headers["authorization"] = f"Bearer {self.access_token}"
                _LOGGER.info("Rise Gardens authentication successful")
                return True
            else:
                _LOGGER.error("Rise Gardens authentication failed: %s", response.text)
                return False
        except Exception as ex:
            _LOGGER.error("Rise Gardens authentication error: %s", ex)
            return False

    def get_gardens_list(self) -> dict[str, Any] | None:
        """Get list of gardens."""
        url = f"{API_BASE}/gardens/list_v2"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception as ex:
            _LOGGER.error("Error fetching gardens list: %s", ex)
        return None

    def get_gardens_device_data(self) -> dict[str, Any] | None:
        """Get device data for all gardens."""
        url = f"{API_BASE}/gardens/gardens_device_data"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception as ex:
            _LOGGER.error("Error fetching gardens device data: %s", ex)
        return None

    def get_light_schedule(self, garden_id: int) -> dict[str, Any] | None:
        """Get light schedule for a garden."""
        url = f"{API_BASE}/device/light-schedule"
        params = {"garden_id": garden_id}
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception as ex:
            _LOGGER.error("Error fetching light schedule: %s", ex)
        return None

    def set_light_level(self, garden_id: int, level: int) -> bool:
        """Set light intensity (0-100)."""
        url = f"{API_BASE}/gardens/{garden_id}/device/light-level"
        payload = {"light_level": level}
        try:
            response = requests.put(url, json=payload, headers=self.headers, timeout=30)
            return response.status_code == 200
        except Exception as ex:
            _LOGGER.error("Error setting light level: %s", ex)
            return False

    def get_last_sensor_data(self, garden_id: int) -> dict[str, Any] | None:
        """Get last sensor data for a garden."""
        url = f"{API_BASE}/device/last_data_sensors"
        params = {"garden_id": garden_id}
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception as ex:
            _LOGGER.error("Error fetching sensor data: %s", ex)
        return None

    def set_pump(self, garden_id: int, on: bool = True) -> bool:
        """Turn pump on or off."""
        url = f"{API_BASE}/gardens/{garden_id}/device/pump"
        payload = {"pump": on}
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            return response.status_code == 200
        except Exception as ex:
            _LOGGER.error("Error controlling pump: %s", ex)
            return False

    def get_pump_schedule(self, garden_id: int) -> dict[str, Any] | None:
        """Get pump schedule for a garden."""
        url = f"{API_BASE}/device/pump/schedule"
        params = {"garden_id": garden_id}
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception as ex:
            _LOGGER.error("Error fetching pump schedule: %s", ex)
        return None
