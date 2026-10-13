"""Data update coordinator for the local Rise Garden integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import RiseGardenLocal, RiseLocalError
from .const import CLOCK_MAX_DRIFT, DOMAIN, LAMP_CHANNELS, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class RiseLocalCoordinator(DataUpdateCoordinator):
    """Polls the controller's read commands one at a time (never in parallel)."""

    def __init__(self, hass: HomeAssistant, client: RiseGardenLocal) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> dict:
        """Fetch all values sequentially. The client serialises access."""
        data: dict = {}
        try:
            for ch in LAMP_CHANNELS:
                data[f"lamp{ch}"] = await self.client.get_int(f"lamp {ch}")
            data["pump"] = await self.client.get_int("wpump")
            data["pump_current"] = await self.client.get_int("wpcurrent")
            # 'wpc' -> "<on seconds> <off seconds>"
            try:
                data["pump_cycle"] = [int(v) for v in (await self.client.get("wpc")).split()[:2]]
            except (RiseLocalError, ValueError):
                data["pump_cycle"] = None
            data["light_schedule"] = await self.client.light_schedule()
            data["rssi"] = await self.client.get_int("rssi")
            data["mqtt"] = await self.client.get_int("mqtt")
            # 'time' -> "<epoch> <YYYY-MM-DD HH:MM:SS>"
            try:
                data["time"] = await self.client.get("time")
            except RiseLocalError:
                data["time"] = None
            if data["time"]:
                await self._sync_clock(data["time"])
        except RiseLocalError as err:
            raise UpdateFailed(f"Controller not reachable: {err}") from err

        # If everything came back None the controller is wedged/offline.
        if all(data.get(k) is None for k in ("lamp1", "rssi", "mqtt")):
            raise UpdateFailed("Controller returned no data (may be rebooting)")
        return data

    async def _sync_clock(self, raw_time: str) -> None:
        """Keep the controller's time of day right without internet/NTP.

        Only the time of day can be set (the date is ignored), and the light
        schedule only uses time of day, so drift is measured modulo one day.
        """
        try:
            device = int(raw_time.split()[0])
        except (ValueError, IndexError):
            return
        now = dt_util.utcnow()
        drift = (device - int(now.timestamp())) % 86400
        drift = min(drift, 86400 - drift)
        if drift <= CLOCK_MAX_DRIFT:
            return
        _LOGGER.info("Controller clock is %s s off; setting it to %s UTC", drift, now.strftime("%H:%M:%S"))
        try:
            await self.client.set_clock(now)
        except RiseLocalError as err:
            _LOGGER.warning("Failed to set controller clock: %s", err)
