"""Shared base entity for the Petnovations / CatGenie integration."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PetnovationsCoordinator


class PetnovationsEntity(CoordinatorEntity[PetnovationsCoordinator]):
    """Base entity that ties to one physical CatGenie device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PetnovationsCoordinator, device: dict) -> None:
        super().__init__(coordinator)
        self._manufacturer_id = device.get("manufacturerId", "unknown")

    @property
    def device(self) -> dict:
        """Always read the freshest copy from the coordinator."""
        return self.coordinator.device_by_id(self._manufacturer_id) or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self.device)

    @property
    def device_info(self) -> dict:
        dev = self.device
        return {
            "identifiers": {(DOMAIN, self._manufacturer_id)},
            "name": dev.get("name", "CatGenie"),
            "manufacturer": "Petnovations",
            "model": "CatGenie A.I.",
            "sw_version": dev.get("fwVersion"),
            "hw_version": dev.get("hwRevision"),
            "serial_number": self._manufacturer_id,
        }
