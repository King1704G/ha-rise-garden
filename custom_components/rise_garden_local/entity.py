"""Shared base entity for local Rise Garden entities."""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RiseLocalCoordinator


class RiseLocalEntity(CoordinatorEntity[RiseLocalCoordinator]):
    """Base entity tying everything to the one controller device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RiseLocalCoordinator, unit_id: str) -> None:
        super().__init__(coordinator)
        self._unit_id = unit_id

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self._unit_id)},
            "name": "Rise Garden (local)",
            "manufacturer": "Rise Gardens",
            "model": "Indoor Garden (ESP32 controller)",
            "connections": {("mac", _mac(self._unit_id))} if _mac(self._unit_id) else set(),
        }


def _mac(unit_id: str) -> str | None:
    """Format a 12-hex unit id as a colon MAC for the device registry."""
    u = unit_id.strip().lower()
    if len(u) == 12 and all(c in "0123456789abcdef" for c in u):
        return ":".join(u[i : i + 2] for i in range(0, 12, 2))
    return None
